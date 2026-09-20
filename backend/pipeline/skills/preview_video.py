"""F4 — 预览视频生成 Skill。

基于 F3 主视觉帧图生视频，落盘 mp4 并记录 skill_runs / artifacts。
Spec: docs/backend-docs/pipeline/spec-f4-preview-video-skill.md
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from media.dashscope_video import VideoClient, VideoClientError
from pipeline import store
from pipeline.models import PreviewVideoInput, PreviewVideoOutput, SceneCard

MIN_DURATION_SEC = 5
MAX_DURATION_SEC = 15
MIN_VIDEO_BYTES = 100_000

ANGLE_ORDER = ('front', 'left', 'rear')

DEFAULT_VIDEO_MODEL = 'wan2.7-i2v'
DEFAULT_VIDEO_FALLBACK_MODEL = 'kling-v3-video'
DEFAULT_FLASH_VIDEO_MODEL = 'wan2.6-i2v-flash'


def _env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


def artifact_root() -> Path:
    raw = os.getenv('ARTIFACT_ROOT')
    if raw:
        return Path(raw)
    return Path(__file__).resolve().parents[2] / 'data' / 'artifacts'


def video_dir(pipeline_run_id: str, root: Path | None = None) -> Path:
    base = root or artifact_root()
    return base / pipeline_run_id / 'video'


def primary_model() -> str:
    if _env('VIDEO_TIER', 'standard') == 'flash':
        return _env('VIDEO_FLASH_MODEL', DEFAULT_FLASH_VIDEO_MODEL)
    return _env('VIDEO_MODEL', DEFAULT_VIDEO_MODEL)


def fallback_model() -> str:
    return _env('VIDEO_FALLBACK_MODEL', DEFAULT_VIDEO_FALLBACK_MODEL)


def estimate_cost(duration_sec: int, resolution: str, tier: str | None = None) -> float:
    """粗估成本（元），与 Spec §8 对齐的区间中位。"""
    tier = tier or _env('VIDEO_TIER', 'standard')
    if tier == 'flash':
        base = 1.0
    else:
        base = 2.0 if resolution == '720P' else 5.5
    return round(base * (duration_sec / 5.0), 2)


CAMERA_MOVES = {
    'front': '镜头从主播正机位缓慢向右横移并轻度环绕，逐步露出左侧灯位与背景层次',
    'left': '镜头从左侧机位缓慢向前推进并轻度环绕，展示主灯、柔光箱与背景层次',
    'rear': '镜头从后侧机位缓慢向纵深推进，展示空间动线、理线与房间尺度',
}


def build_motion_prompt(
    scene_card: SceneCard,
    *,
    duration_sec: int,
    resolution: str,
    source_angle: str = 'front',
) -> str:
    """以首帧为锚组装 i2v motion prompt；注入完整 scene_card，禁止品牌 logo / 屏幕文字。"""
    style = ', '.join(k for k in scene_card.style_keywords if k) or '现代专业'
    palette = ', '.join(c for c in scene_card.color_palette if c) or '暖中性'
    furniture = ', '.join(f for f in scene_card.furniture if f) or '直播家具'
    fixtures = ', '.join(f for f in scene_card.lighting_fixtures if f) or '柔光箱'
    product = scene_card.product_category or '通用商品'
    camera = CAMERA_MOVES.get(source_angle, CAMERA_MOVES['front'])

    parts = [
        '以给定首帧图为唯一起点，严格保持画面中的房间结构、家具布置、灯具位置与色彩不变。',
        f'{camera}。',
        (
            f'专业直播间室内，{style}风格，色调 {palette}，'
            f'可见 {furniture} 与 {fixtures}。'
        ),
        (
            f'色温 {scene_card.color_temp}，商品品类 {product}，'
            f'{scene_card.room_size_band} 房间尺度。'
        ),
        '灯光稳定无闪烁，画面干净专业，无人物特写，无文字，无水印，无 logo。',
    ]
    for item in scene_card.forbidden:
        cleaned = str(item).strip()
        if cleaned:
            parts.append(f'不要出现{cleaned}。')
    parts.append(f'镜头运动平滑电影感，时长约 {duration_sec} 秒，画质 {resolution}。')
    return ' '.join(parts)


def select_source_image(
    images: list[dict[str, Any]],
    source_angle: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    """首帧选择：优先 source_angle，缺失则 front → left → rear。"""
    warnings: list[str] = []
    by_angle: dict[str, dict[str, Any]] = {}
    for item in images:
        angle = str(item.get('angle') or '').lower()
        path = item.get('path')
        if angle in ANGLE_ORDER and path:
            by_angle[angle] = item

    if source_angle in by_angle:
        return by_angle[source_angle], warnings

    warnings.append(f'机位 {source_angle} 缺失，按 front→left→rear 顺延')
    for angle in ANGLE_ORDER:
        if angle in by_angle:
            return by_angle[angle], warnings
    return None, warnings


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
    except Exception as exc:  # pydantic ValidationError
        warnings.append(f'scene_card 校验失败: {exc}')
        return SceneCard(), warnings


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _probe_duration_sec(path: Path) -> float | None:
    if not shutil.which('ffprobe'):
        return None
    try:
        proc = subprocess.run(
            [
                'ffprobe', '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                str(path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    try:
        return float(proc.stdout.strip())
    except ValueError:
        return None


def _validate_duration(duration_sec: int) -> str | None:
    if not (MIN_DURATION_SEC <= duration_sec <= MAX_DURATION_SEC):
        return f'duration_sec 必须在 [{MIN_DURATION_SEC}, {MAX_DURATION_SEC}]，当前 {duration_sec}'
    return None


async def _generate_once(
    client: VideoClient,
    *,
    model: str,
    prompt: str,
    image_path: Path,
    duration_sec: int,
    resolution: str,
    dest: Path,
    timeout_sec: float,
) -> Path:
    task_id = await client.submit_i2v(
        model=model,
        prompt=prompt,
        image_path=image_path,
        duration_sec=duration_sec,
        resolution=resolution,
    )
    result = await client.wait_task(task_id, timeout_sec=timeout_sec)
    assert result.video_url
    await client.download(result.video_url, dest)
    return dest


def _output_failed(
    *,
    error: str,
    warnings: list[str],
    resolution: str,
    duration_sec: float,
    model: str,
    cost_cny: float,
    source_image: str | None = None,
) -> PreviewVideoOutput:
    return PreviewVideoOutput(
        status='failed',
        video_path=None,
        source_image=source_image,
        duration_sec=duration_sec,
        resolution=resolution,
        model=model,
        sha256='',
        cost_cny=cost_cny,
        warnings=warnings,
        error=error,
    )


def _reuse_existing(pipeline_run_id: str, warnings: list[str]) -> PreviewVideoOutput | None:
    existing = store.find_latest_video_artifact(pipeline_run_id)
    if not existing:
        return None
    path = existing['path']
    meta = existing.get('meta') or {}
    if not store.video_file_usable(path, MIN_VIDEO_BYTES):
        warnings.append('已有 video artifact 不可用，重新生成')
        return None
    return PreviewVideoOutput(
        status='succeeded',
        video_path=path,
        source_image=meta.get('source_image'),
        duration_sec=float(meta.get('duration_sec') or 0.0),
        resolution=str(meta.get('resolution') or ''),
        model=str(meta.get('model') or ''),
        sha256=str(existing.get('sha256') or meta.get('sha256') or ''),
        cost_cny=float(meta.get('cost_cny') or 0.0),
        warnings=warnings + ['复用已成功预览视频'],
        error=None,
        reused=True,
    )


async def run_preview_video(
    inp: PreviewVideoInput,
    *,
    client: VideoClient | None = None,
    root: Path | None = None,
    timeout_sec: float | None = None,
) -> PreviewVideoOutput:
    """执行 F4 流水线：Select → Prompt → Submit → Poll → Download → Verify → Persist。"""
    warnings: list[str] = []
    duration_err = _validate_duration(inp.duration_sec)
    run_id = store.start_skill_run(
        inp.pipeline_run_id,
        'preview_video',
        input_payload=inp.model_dump(),
    )

    def _fail(error: str, *, cost_cny: float = 0.0, model: str = '', source_image: str | None = None) -> PreviewVideoOutput:
        out = _output_failed(
            error=error,
            warnings=warnings,
            resolution=inp.resolution,
            duration_sec=float(inp.duration_sec),
            model=model,
            cost_cny=cost_cny,
            source_image=source_image,
        )
        store.finish_skill_run(
            run_id,
            status='failed',
            output=out.model_dump(),
            cost_cny=cost_cny,
            error=error,
        )
        return out

    if duration_err:
        return _fail(duration_err)

    if not inp.force:
        reused = _reuse_existing(inp.pipeline_run_id, warnings)
        if reused is not None:
            store.finish_skill_run(
                run_id,
                status='succeeded',
                output=reused.model_dump(),
                cost_cny=reused.cost_cny,
            )
            return reused

    source, select_warnings = select_source_image(inp.images, inp.source_angle)
    warnings.extend(select_warnings)
    if source is None:
        return _fail('无可用 F3 预览图，无法生成预览视频')

    source_path = Path(str(source['path']))
    if not source_path.is_file():
        return _fail(f'首帧图文件不存在: {source_path}', source_image=str(source_path))

    scene_card, scene_warnings = load_scene_card(inp.plan_json_path)
    warnings.extend(scene_warnings)
    source_angle = str(source.get('angle') or inp.source_angle or 'front')
    prompt = build_motion_prompt(
        scene_card,
        duration_sec=inp.duration_sec,
        resolution=inp.resolution,
        source_angle=source_angle,
    )

    out_dir = video_dir(inp.pipeline_run_id, root)
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / 'preview.mp4'
    meta_path = out_dir / 'meta.json'

    owns_client = client is None
    if client is None:
        from media.factory import get_video_client

        client = get_video_client()
    budget = timeout_sec if timeout_sec is not None else float(os.getenv('VIDEO_TIMEOUT_SEC', '300'))

    models_to_try = [primary_model(), fallback_model()]
    # 先按请求分辨率试；1080P 失败后降 720P（每个模型各一次）
    resolutions_to_try: list[str] = [inp.resolution]
    if inp.resolution == '1080P':
        resolutions_to_try.append('720P')

    cost_cny = 0.0
    used_model = models_to_try[0]
    used_resolution = inp.resolution
    last_error = '未知错误'

    try:
        for model in models_to_try:
            used_model = model
            for resolution in resolutions_to_try:
                used_resolution = resolution
                attempt_cost = estimate_cost(inp.duration_sec, resolution)
                if dest.exists():
                    dest.unlink(missing_ok=True)
                try:
                    await _generate_once(
                        client,
                        model=model,
                        prompt=prompt,
                        image_path=source_path,
                        duration_sec=inp.duration_sec,
                        resolution=resolution,
                        dest=dest,
                        timeout_sec=budget,
                    )
                except VideoClientError as exc:
                    last_error = str(exc)
                    warnings.append(f'{model}@{resolution} 失败: {exc}')
                    continue

                if not dest.is_file() or dest.stat().st_size < MIN_VIDEO_BYTES:
                    last_error = f'视频文件无效或过小（<{MIN_VIDEO_BYTES}B）'
                    warnings.append(last_error)
                    # 损坏文件：同配置重试一次
                    try:
                        await _generate_once(
                            client,
                            model=model,
                            prompt=prompt,
                            image_path=source_path,
                            duration_sec=inp.duration_sec,
                            resolution=resolution,
                            dest=dest,
                            timeout_sec=budget,
                        )
                    except VideoClientError as exc:
                        last_error = str(exc)
                        warnings.append(f'重试仍失败: {exc}')
                        continue
                    if not dest.is_file() or dest.stat().st_size < MIN_VIDEO_BYTES:
                        last_error = f'重试后视频文件仍无效（<{MIN_VIDEO_BYTES}B）'
                        warnings.append(last_error)
                        continue

                probe = _probe_duration_sec(dest)
                if probe is not None:
                    low = inp.duration_sec - 1
                    high = inp.duration_sec + 2
                    if probe < low or probe > high:
                        last_error = f'视频时长 {probe:.2f}s 超出 [{low}, {high}]'
                        warnings.append(last_error)
                        continue

                if resolution != inp.resolution:
                    warnings.append(f'{inp.resolution} 失败，已降级为 {resolution}')

                cost_cny += attempt_cost
                sha = _sha256_file(dest)
                meta = {
                    'pipeline_run_id': inp.pipeline_run_id,
                    'source_image': str(source_path),
                    'source_angle': source.get('angle'),
                    'duration_sec': inp.duration_sec,
                    'resolution': resolution,
                    'model': model,
                    'sha256': sha,
                    'cost_cny': attempt_cost,
                    'prompt': prompt,
                    'video_path': str(dest),
                    'probe_duration_sec': probe,
                }
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')
                store.save_artifact(
                    inp.pipeline_run_id,
                    'video',
                    str(dest),
                    sha256=sha,
                    meta=meta,
                )

                out = PreviewVideoOutput(
                    status='succeeded',
                    video_path=str(dest),
                    source_image=str(source_path),
                    duration_sec=float(inp.duration_sec),
                    resolution=resolution,
                    model=model,
                    sha256=sha,
                    cost_cny=cost_cny,
                    warnings=warnings,
                    error=None,
                    reused=False,
                )
                store.finish_skill_run(
                    run_id,
                    status='succeeded',
                    output=out.model_dump(),
                    cost_cny=cost_cny,
                )
                return out

        return _fail(last_error, cost_cny=cost_cny, model=used_model, source_image=str(source_path))
    finally:
        if owns_client and hasattr(client, 'aclose'):
            await client.aclose()  # type: ignore[attr-defined]
