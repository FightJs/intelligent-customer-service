"""F3 — 三机位预览图生成 Skill。

基于 F2 plan.json / scene_card 生成 front/left/rear 连贯静帧。
Spec: docs/backend-docs/pipeline/spec-f3-preview-images-skill.md
"""
from __future__ import annotations

import hashlib
import json
import os
import random
from pathlib import Path
from typing import Any

from media.dashscope_image import ImageClient, ImageClientError, is_valid_png
from pipeline import store
from pipeline.models import PreviewImageItem, PreviewImagesInput, PreviewImagesOutput, SceneCard

ANGLE_ORDER = ('front', 'left', 'rear')

ANGLE_PROMPTS = {
    'front': 'camera at host position, facing product display wall, front view of livestream set',
    'left': 'camera at left side 120 degrees, show key lights, softboxes, background layers',
    'rear': 'camera at rear-right 240 degrees, show cable management, walking path, depth of room',
}

ANGLE_LABELS = {
    'front': '正面 0°',
    'left': '左侧 120°',
    'rear': '背面 240°',
}

DEFAULT_IMAGE_MODEL = 'wan2.7-image'
DEFAULT_IMAGE_FALLBACK_MODEL = 'qwen-image'

QUALITY_SIZE = {
    'draft': '1024*1024',
    'standard': '1280*720',
    'high': '1920*1080',
}

QUALITY_COST_CNY = {
    'draft': 0.15,
    'standard': 0.5,
    'high': 1.5,
}


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def artifact_root() -> Path:
    raw = os.getenv('ARTIFACT_ROOT')
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[2] / 'data' / 'artifacts'


def images_dir(pipeline_run_id: str, root: Path | None = None) -> Path:
    base = root or artifact_root()
    return base / pipeline_run_id / 'images'


def primary_model() -> str:
    return _env('IMAGE_MODEL', DEFAULT_IMAGE_MODEL)


def fallback_model() -> str:
    return _env('IMAGE_FALLBACK_MODEL', DEFAULT_IMAGE_FALLBACK_MODEL)


def estimate_cost(quality: str, count: int) -> float:
    return round(QUALITY_COST_CNY.get(quality, QUALITY_COST_CNY['standard']) * max(count, 1), 2)


def build_common_lock(scene_card: SceneCard) -> str:
    palette = ', '.join(c for c in scene_card.color_palette if c) or 'warm neutral'
    style = ', '.join(k for k in scene_card.style_keywords if k) or 'professional'
    furniture = ', '.join(f for f in scene_card.furniture if f) or 'livestream furniture'
    fixtures = ', '.join(f for f in scene_card.lighting_fixtures if f) or 'softboxes'
    product = scene_card.product_category or 'general merchandise'
    parts = [
        'same room, same furniture set, same lighting setup,',
        f'same color palette {palette},',
        'professional livestream studio interior, photorealistic,',
        'shot on full-frame camera, natural perspective, real materials and fabric texture,',
        'soft realistic shadows, practical lighting fixtures, lived-in commercial set,',
        'no text, no watermark, no logo,',
        f'{style} style,',
        f'room size {scene_card.room_size_band},',
        f'product category {product},',
        f'lighting: {fixtures},',
        f'furniture: {furniture},',
        f'color temperature {scene_card.color_temp}',
    ]
    return ' '.join(parts)


def build_angle_prompt(scene_card: SceneCard, angle: str) -> str:
    common = build_common_lock(scene_card)
    angle_part = ANGLE_PROMPTS.get(angle, ANGLE_PROMPTS['front'])
    forbidden_parts = []
    for item in scene_card.forbidden:
        cleaned = str(item).strip()
        if cleaned:
            forbidden_parts.append(f'no {cleaned}')
    forbidden = (' ' + ' '.join(forbidden_parts)) if forbidden_parts else ''
    return f'{common}, {angle_part}{forbidden}'


def load_scene_card(plan_json_path: str) -> tuple[SceneCard, list[str]]:
    warnings: list[str] = []
    path = Path(plan_json_path)
    if not path.is_file():
        warnings.append(f'plan.json 不存在: {plan_json_path}')
        return SceneCard(), warnings
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as exc:
        warnings.append(f'plan.json 读取失败: {exc}')
        return SceneCard(), warnings
    raw = data.get('scene_card') if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        warnings.append('plan.json 缺少 scene_card')
        return SceneCard(), warnings
    try:
        return SceneCard.model_validate(raw), warnings
    except Exception as exc:
        warnings.append(f'scene_card 校验失败: {exc}')
        return SceneCard(), warnings


def resolve_angles(scene_card: SceneCard, image_count: int) -> list[str]:
    angles = [a for a in (scene_card.camera_angles or ANGLE_ORDER) if a in ANGLE_ORDER]
    if not angles:
        angles = list(ANGLE_ORDER)
    # 保证 front 优先，再 left → rear
    ordered = [a for a in ANGLE_ORDER if a in angles]
    if image_count and image_count < len(ordered):
        ordered = ordered[: max(image_count, 1)]
    return ordered


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _image_size(path: Path) -> tuple[int, int]:
    try:
        from PIL import Image

        with Image.open(path) as img:
            return int(img.width), int(img.height)
    except Exception:
        return 0, 0


def _existing_success(
    pipeline_run_id: str,
    angles: list[str],
    *,
    root: Path | None = None,
    min_count: int = 3,
) -> list[PreviewImageItem] | None:
    """磁盘上已有全部目标机位成功图时返回复用列表，否则 None。"""
    out_dir = images_dir(pipeline_run_id, root)
    items: list[PreviewImageItem] = []
    for angle in angles:
        path = out_dir / f'preview_{angle}.png'
        if not is_valid_png(path):
            return None
        width, height = _image_size(path)
        items.append(
            PreviewImageItem(
                angle=angle,
                path=str(path),
                width=width,
                height=height,
                sha256=_sha256_file(path),
                model='',
                cost_cny=0.0,
                seed=None,
            )
        )
    return items if items else None


def _partial_existing(
    pipeline_run_id: str,
    angles: list[str],
    *,
    root: Path | None = None,
) -> list[PreviewImageItem]:
    out_dir = images_dir(pipeline_run_id, root)
    items: list[PreviewImageItem] = []
    for angle in angles:
        path = out_dir / f'preview_{angle}.png'
        if not is_valid_png(path):
            continue
        width, height = _image_size(path)
        items.append(
            PreviewImageItem(
                angle=angle,
                path=str(path),
                width=width,
                height=height,
                sha256=_sha256_file(path),
                model='',
                cost_cny=0.0,
                seed=None,
            )
        )
    return items


def _write_manifest(
    out_dir: Path,
    *,
    pipeline_run_id: str,
    images: list[PreviewImageItem],
    seed_used: int | None,
    model: str,
    quality: str,
    total_cost: float,
    status: str,
) -> None:
    payload = {
        'pipeline_run_id': pipeline_run_id,
        'status': status,
        'seed_used': seed_used,
        'model': model,
        'quality': quality,
        'total_cost_cny': total_cost,
        'images': [img.model_dump() for img in images],
        'angle_labels': ANGLE_LABELS,
    }
    (out_dir / 'manifest.json').write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding='utf-8',
    )


async def _generate_one(
    client: ImageClient,
    *,
    model: str,
    prompt: str,
    seed: int,
    size: str,
    dest: Path,
    timeout_sec: float,
) -> tuple[Path, int | None]:
    task_id = await client.submit_t2i(
        model=model,
        prompt=prompt,
        seed=seed,
        size=size,
        n=1,
    )
    result = await client.wait_task(task_id, timeout_sec=timeout_sec)
    if not result.image_urls:
        raise ImageClientError('任务成功但无图片 URL')
    await client.download(result.image_urls[0], dest)
    if not is_valid_png(dest):
        dest.unlink(missing_ok=True)
        raise ImageClientError('生成图损坏或过小', retryable=True)
    return dest, result.seed if result.seed is not None else seed


def _output_failed(
    *,
    error: str,
    warnings: list[str],
    images: list[PreviewImageItem],
    seed_used: int | None,
    model: str,
    cost_cny: float,
    status: str = 'failed',
) -> PreviewImagesOutput:
    return PreviewImagesOutput(
        status=status,  # type: ignore[arg-type]
        images=images,
        seed_used=seed_used,
        model=model,
        total_cost_cny=cost_cny,
        warnings=warnings,
        error=error,
    )


async def run_preview_images(
    inp: PreviewImagesInput,
    *,
    client: ImageClient | None = None,
    root: Path | None = None,
    timeout_sec: float | None = None,
) -> PreviewImagesOutput:
    """执行 F3：Load → Prompt → Submit → Poll → Download → Verify → Persist。"""
    warnings: list[str] = []
    run_id = store.start_skill_run(
        inp.pipeline_run_id,
        'preview_images',
        input_payload=inp.model_dump(mode='json'),
    )

    def _finish(out: PreviewImagesOutput) -> PreviewImagesOutput:
        status = out.status
        if status == 'succeeded':
            store_status = 'succeeded'
        elif status == 'partial':
            store_status = 'partial'
        else:
            store_status = 'failed'
        store.finish_skill_run(
            run_id,
            status=store_status,
            output=out.model_dump(mode='json'),
            cost_cny=out.total_cost_cny,
            error=out.error,
        )
        if out.images:
            out_dir = images_dir(inp.pipeline_run_id, root)
            out_dir.mkdir(parents=True, exist_ok=True)
            _write_manifest(
                out_dir,
                pipeline_run_id=inp.pipeline_run_id,
                images=out.images,
                seed_used=out.seed_used,
                model=out.model,
                quality=inp.quality,
                total_cost=out.total_cost_cny,
                status=out.status,
            )
        return out

    scene_card, scene_warnings = load_scene_card(inp.plan_json_path)
    warnings.extend(scene_warnings)
    angles = resolve_angles(scene_card, inp.image_count)
    out_dir = images_dir(inp.pipeline_run_id, root)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not inp.force:
        reused = _existing_success(
            inp.pipeline_run_id,
            angles,
            root=root,
            min_count=min(3, len(angles)),
        )
        if reused is not None:
            out = PreviewImagesOutput(
                status='succeeded',
                images=reused,
                seed_used=None,
                model=reused[0].model if reused else '',
                total_cost_cny=0.0,
                warnings=warnings + ['复用已有预览图，未重新生成'],
                error=None,
            )
            return _finish(out)

        # partial 重试：跳过已成功机位
        existing_by_angle = {
            img.angle: img for img in _partial_existing(inp.pipeline_run_id, angles, root=root)
        }
        missing_angles = [a for a in angles if a not in existing_by_angle]
        if not missing_angles:
            items = [existing_by_angle[a] for a in angles if a in existing_by_angle]
            out = PreviewImagesOutput(
                status='succeeded',
                images=items,
                seed_used=None,
                model='',
                total_cost_cny=0.0,
                warnings=warnings + ['全部机位已存在，复用'],
                error=None,
            )
            return _finish(out)
    else:
        existing_by_angle = {}
        missing_angles = list(angles)

    owns_client = client is None
    if client is None:
        from media.factory import get_image_client

        client = get_image_client()

    budget = timeout_sec if timeout_sec is not None else float(os.getenv('IMAGE_TIMEOUT_SEC', '180'))
    size = QUALITY_SIZE.get(inp.quality, QUALITY_SIZE['standard'])
    seed = random.randint(1, 2**31 - 1)
    cost_cny = 0.0
    per_image_cost = QUALITY_COST_CNY.get(inp.quality, QUALITY_COST_CNY['standard'])
    models_to_try = [primary_model(), fallback_model()]
    model_used = models_to_try[0]

    produced: list[PreviewImageItem] = []
    try:
        for angle in missing_angles:
            prompt = build_angle_prompt(scene_card, angle)
            dest = out_dir / f'preview_{angle}.png'
            success = False
            last_error = '未知错误'
            for model in models_to_try:
                model_used = model
                try:
                    dest.unlink(missing_ok=True)
                    path, used_seed = await _generate_one(
                        client,
                        model=model,
                        prompt=prompt,
                        seed=seed,
                        size=size,
                        dest=dest,
                        timeout_sec=budget,
                    )
                except ImageClientError as exc:
                    last_error = str(exc)
                    warnings.append(f'{angle}@{model} 失败: {exc}')
                    continue

                # 损坏图再试一次
                if not is_valid_png(path):
                    last_error = '生成图损坏'
                    warnings.append(f'{angle} 生成图损坏，重试')
                    try:
                        path, used_seed = await _generate_one(
                            client,
                            model=model,
                            prompt=prompt,
                            seed=seed,
                            size=size,
                            dest=dest,
                            timeout_sec=budget,
                        )
                    except ImageClientError as exc:
                        last_error = str(exc)
                        warnings.append(f'{angle} 重试仍失败: {exc}')
                        continue
                    if not is_valid_png(path):
                        last_error = '重试后生成图仍损坏'
                        warnings.append(last_error)
                        continue

                width, height = _image_size(path)
                sha = _sha256_file(path)
                cost_cny += per_image_cost
                if used_seed is not None:
                    seed = used_seed
                item = PreviewImageItem(
                    angle=angle,
                    path=str(path),
                    width=width,
                    height=height,
                    sha256=sha,
                    model=model,
                    cost_cny=per_image_cost,
                    seed=used_seed,
                )
                produced.append(item)
                store.save_artifact(
                    inp.pipeline_run_id,
                    f'image_{angle}',
                    str(path),
                    sha256=sha,
                    meta={
                        'angle': angle,
                        'label': ANGLE_LABELS.get(angle, angle),
                        'seed': used_seed,
                        'model': model,
                        'width': width,
                        'height': height,
                        'cost_cny': per_image_cost,
                        'prompt': prompt,
                    },
                )
                success = True
                break

        all_angles_ok = {img.angle for img in produced} | set(existing_by_angle)
        final_items: list[PreviewImageItem] = []
        for angle in angles:
            if angle in {img.angle for img in produced}:
                final_items.append(next(img for img in produced if img.angle == angle))
            elif angle in existing_by_angle:
                final_items.append(existing_by_angle[angle])

        if len(final_items) == 0:
            out = _output_failed(
                error='预览图全部失败',
                warnings=warnings,
                images=[],
                seed_used=seed,
                model=model_used,
                cost_cny=cost_cny,
            )
            return _finish(out)

        if len(final_items) < len(angles):
            if not inp.allow_partial:
                out = _output_failed(
                    error=f'仅成功 {len(final_items)}/{len(angles)} 张且不允许 partial',
                    warnings=warnings,
                    images=final_items,
                    seed_used=seed,
                    model=model_used,
                    cost_cny=cost_cny,
                )
                return _finish(out)
            missing = [a for a in angles if a not in all_angles_ok]
            warnings.append(f'缺失机位: {", ".join(missing)}')
            out = PreviewImagesOutput(
                status='partial',
                images=final_items,
                seed_used=seed,
                model=model_used,
                total_cost_cny=cost_cny,
                warnings=warnings,
                error=None,
            )
            return _finish(out)

        out = PreviewImagesOutput(
            status='succeeded',
            images=final_items,
            seed_used=seed,
            model=model_used,
            total_cost_cny=cost_cny,
            warnings=warnings,
            error=None,
        )
        return _finish(out)
    finally:
        if owns_client and hasattr(client, 'aclose'):
            await client.aclose()  # type: ignore[attr-defined]
