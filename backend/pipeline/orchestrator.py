"""F2→F5 编排器：状态机、超时、重试、取消、成本汇总。

Skill 顺序：plan_document → preview_images → preview_video → final_package
F1 在 F2 内部作为检索依赖，不单独成为 pipeline 阶段。
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from pipeline.artifacts import get_artifact_root
from pipeline.final_package import run_final_package
from pipeline.models import (
    FinalPackageInput,
    PlanDocumentInput,
    PlanDocumentOutput,
    PreviewImagesInput,
    PreviewImagesOutput,
    PreviewVideoInput,
    PreviewVideoOutput,
)
from pipeline.plan_document import run_plan_document
from pipeline.skills.preview_images import run_preview_images
from pipeline.skills.preview_video import run_preview_video
from store import db

logger = logging.getLogger(__name__)

SKILL_ORDER = ('plan_document', 'preview_images', 'preview_video', 'final_package')

# 前端 PlanDetail.skills 键名映射
SKILL_UI_KEY = {
    'plan_document': 'plan',
    'preview_images': 'images',
    'preview_video': 'video',
    'final_package': 'package',
}

TIMEOUT_SEC = {
    'plan_document': 120.0,
    # 中转站串行 3 张可能 >180s
    'preview_images': 360.0,
    'preview_video': 360.0,
    'final_package': 60.0,
}

# 编排层认为“该阶段继续推进”的最低状态
UPSTREAM_OK = {'succeeded', 'degraded', 'partial', 'ready', 'ready_with_warnings'}


class PipelineCancelled(Exception):
    """用户取消后中断编排。"""


def _is_cancelled(pipeline_run_id: str) -> bool:
    rec = db.get_pipeline_run(pipeline_run_id)
    return bool(rec and rec['status'] == 'cancelled')


def _load_session_context(session_id: str) -> tuple[dict[str, Any], int | None]:
    rec = db.get_session(session_id)
    if rec is None:
        raise ValueError(f'会话不存在: {session_id}')
    form_state = rec.get('form_state') or {}
    if not isinstance(form_state, dict):
        form_state = {}
    # delivery 可选
    delivery = db.get_delivery_by_session(session_id)
    delivery_id = delivery['id'] if delivery else None
    return form_state, delivery_id


def build_pipeline_detail(pipeline_run_id: str) -> dict[str, Any] | None:
    """组装 GET /api/pipeline/{id} 响应（对齐前端 PlanDetail）。"""
    run = db.get_pipeline_run(pipeline_run_id)
    if run is None:
        return None

    skill_status = db.latest_skill_status_map(pipeline_run_id)
    skills_ui = {
        UI_KEY: skill_status.get(skill, 'pending')
        for skill, UI_KEY in SKILL_UI_KEY.items()
    }
    # 映射 orchestrator/skill 状态到前端 SkillState
    status_alias = {
        'succeeded': 'succeeded',
        'degraded': 'succeeded',
        'partial': 'partial',
        'ready': 'succeeded',
        'ready_with_warnings': 'succeeded',
        'failed': 'failed',
        'running': 'running',
        'pending': 'pending',
        'cancelled': 'failed',
    }
    for key, raw in list(skills_ui.items()):
        skills_ui[key] = status_alias.get(raw, raw if raw in status_alias.values() else 'pending')

    artifacts = db.list_artifacts(pipeline_run_id)
    images: list[dict[str, Any]] = []
    video: dict[str, Any] | None = None
    pdf: dict[str, Any] | None = None
    package_file_count: int | None = None
    plan_meta: dict[str, Any] = {}
    plan_content: dict[str, Any] | None = None

    for art in artifacts:
        kind = art.get('kind') or ''
        path = art.get('path') or ''
        meta = {}
        if art.get('meta_json'):
            import json

            try:
                meta = json.loads(art['meta_json'])
            except json.JSONDecodeError:
                meta = {}
        if kind.startswith('image_'):
            angle = kind.replace('image_', '', 1)
            if Path(path).is_file():
                images.append(
                    {
                        'angle': angle,
                        'label': meta.get('label') or angle,
                        'name': meta.get('label') or angle,
                        'url': f'/api/pipeline/{pipeline_run_id}/artifacts/{kind}',
                        'width': meta.get('width') or 0,
                        'height': meta.get('height') or 0,
                        'sha256': art.get('sha256') or '',
                        'missing': False,
                    }
                )
        elif kind == 'video' and Path(path).is_file():
            video = {
                'durationSec': float(meta.get('duration_sec') or 0),
                'resolution': meta.get('resolution') or '',
                'url': f'/api/pipeline/{pipeline_run_id}/artifacts/video',
                'sha256': art.get('sha256') or '',
            }
        elif kind == 'plan_pdf' and Path(path).is_file():
            pdf = {
                'title': '直播间搭建方案',
                'sections': ['需求摘要', '空间布局', '设备清单', '三档套餐', '搭建步骤', '风险提示'],
                'url': f'/api/pipeline/{pipeline_run_id}/artifacts/plan_pdf',
            }
        elif kind == 'plan_json':
            try:
                import json

                plan_data = json.loads(Path(path).read_text(encoding='utf-8'))
                if isinstance(plan_data, dict):
                    plan_meta = plan_data.get('meta') or {}
                    plan_content = plan_data
            except Exception:
                plan_meta = {}
                plan_content = None

    # 补齐缺失机位占位
    expected_angles = ['front', 'left', 'rear']
    present = {img['angle'] for img in images}
    for angle in expected_angles:
        if angle not in present:
            images.append(
                {
                    'angle': angle,
                    'label': angle,
                    'name': '缺失',
                    'url': '',
                    'width': 0,
                    'height': 0,
                    'sha256': '',
                    'missing': True,
                }
            )
    images.sort(key=lambda x: expected_angles.index(x['angle']) if x['angle'] in expected_angles else 99)

    if skills_ui.get('video') == 'failed':
        video = {'failed': True, 'message': '预览视频生成失败，可重试该 skill'}

    # package 文件数
    package_ready = skills_ui.get('package') in {'succeeded', 'partial'}
    if package_ready:
        from pipeline.final_package import package_dir_for

        pkg = package_dir_for(pipeline_run_id)
        if pkg.is_dir():
            package_file_count = sum(1 for f in pkg.rglob('*') if f.is_file())

    run_status = run['status']
    # 对齐前端 PlanStatus
    plan_status_map = {
        'pending': 'pending',
        'running': 'running',
        'ready': 'ready',
        'ready_with_warnings': 'partial' if skills_ui.get('images') == 'partial' or skills_ui.get('video') == 'failed' else 'ready',
        'failed': 'failed',
        'cancelled': 'failed',
    }
    if run_status == 'ready_with_warnings' and skills_ui.get('package') == 'succeeded':
        if skills_ui.get('images') == 'partial' or skills_ui.get('video') == 'failed':
            plan_status = 'partial'
        else:
            plan_status = 'ready'
    else:
        plan_status = plan_status_map.get(run_status, 'running')

    title = plan_meta.get('brand') or '直播间方案'
    industry = plan_meta.get('industry') or ''
    room_size = plan_meta.get('room_size') or ''
    budget = plan_meta.get('budget_total') or ''

    skill_runs = db.list_skill_runs(pipeline_run_id)
    total_cost = round(sum(float(s.get('cost_cny') or 0) for s in skill_runs), 6)

    return {
        'id': pipeline_run_id,
        'title': title,
        'industry': industry,
        'roomSize': room_size,
        'budget': budget,
        'status': plan_status,
        'raw_status': run_status,
        'current_skill': run.get('current_skill'),
        'session_id': run.get('session_id'),
        'delivery_id': run.get('delivery_id'),
        'user_id': run.get('user_id'),
        'error': run.get('error'),
        'created_at': run.get('created_at'),
        'updated_at': run.get('updated_at'),
        'skills': skills_ui,
        'images': images,
        'video': video,
        'pdf': pdf,
        'plan': plan_content,
        'packageFileCount': package_file_count,
        'total_cost_cny': total_cost,
        'skill_runs': [
            {
                'id': s['id'],
                'skill': s['skill'],
                'status': s['status'],
                'attempt': s.get('attempt') or 1,
                'cost_cny': s.get('cost_cny') or 0,
                'error': s.get('error'),
                'started_at': s.get('started_at'),
                'finished_at': s.get('finished_at'),
            }
            for s in skill_runs
        ],
    }


async def _run_with_timeout(coro, timeout_sec: float, skill: str):
    try:
        return await asyncio.wait_for(coro, timeout=timeout_sec)
    except asyncio.TimeoutError as exc:
        raise TimeoutError(f'{skill} 超时（>{timeout_sec:.0f}s）') from exc


def _run_final_package_tracked(
    pipeline_run_id: str,
    final_inp: FinalPackageInput,
    *,
    root: Path,
    readme_llm=None,
):
    """执行 F5 并写入 skill_runs / artifacts。"""
    from pipeline import store as pipeline_store

    run_id = pipeline_store.start_skill_run(
        pipeline_run_id,
        'final_package',
        input_payload=final_inp.model_dump(mode='json', exclude={'plan_output', 'images_output', 'video_output'}),
    )
    out = run_final_package(final_inp, artifact_root_override=root, readme_llm=readme_llm)
    status = out.status if out.status in {'ready', 'ready_with_warnings', 'failed'} else 'failed'
    # total_cost_cny 含上游；skill_run 只记 F5 自身增量，避免双计
    try:
        upstream = (
            float((final_inp.plan_output or {}).get('cost_cny') or 0)
            + float((final_inp.images_output or {}).get('total_cost_cny') or 0)
            + float((final_inp.video_output or {}).get('cost_cny') or 0)
        )
        skill_cost = max(round(float(out.total_cost_cny) - upstream, 6), 0.0)
    except Exception:
        skill_cost = 0.0
    pipeline_store.finish_skill_run(
        run_id,
        status=status,
        output=out.model_dump(mode='json'),
        cost_cny=skill_cost,
        error=out.error,
    )
    if out.package_dir:
        db.upsert_artifact(
            pipeline_run_id=pipeline_run_id,
            kind='package_dir',
            path=out.package_dir,
        )
    if out.zip_path and Path(out.zip_path).is_file():
        from pipeline.packager import sha256_file

        db.upsert_artifact(
            pipeline_run_id=pipeline_run_id,
            kind='package_zip',
            path=out.zip_path,
            sha256=sha256_file(Path(out.zip_path)),
        )
    return out


async def run_pipeline(
    pipeline_run_id: str,
    *,
    form_state: dict[str, Any] | None = None,
    llm_json=None,
    search_fn=None,
    image_client=None,
    video_client=None,
    readme_llm=None,
    artifact_root: Path | None = None,
    skip_plan: bool = False,
) -> dict[str, Any]:
    """执行完整管线。返回 build_pipeline_detail 结果。"""
    run = db.get_pipeline_run(pipeline_run_id)
    if run is None:
        raise ValueError(f'pipeline_run 不存在: {pipeline_run_id}')

    if form_state is None:
        form_state, delivery_id_from_session = _load_session_context(run['session_id'])
        if run.get('delivery_id') is None and delivery_id_from_session is not None:
            db.update_pipeline_run(pipeline_run_id, delivery_id=delivery_id_from_session)
    else:
        delivery_id_from_session = run.get('delivery_id')

    root = artifact_root or get_artifact_root()
    session_id = run['session_id']
    delivery_id = run.get('delivery_id') or delivery_id_from_session

    db.update_pipeline_run(pipeline_run_id, status='running', current_skill='plan_document')

    plan_out: PlanDocumentOutput | None = None
    images_out: PreviewImagesOutput | None = None
    video_out: PreviewVideoOutput | None = None

    try:
        # ── F2 plan_document ─────────────────────────────
        if _is_cancelled(pipeline_run_id):
            raise PipelineCancelled()

        db.update_pipeline_run(pipeline_run_id, current_skill='plan_document')
        if skip_plan:
            from pipeline.artifacts import try_reuse_plan

            reused = try_reuse_plan(pipeline_run_id, root)
            if reused is None:
                raise RuntimeError('skip_plan 但无已有 plan.json')
            plan_out = PlanDocumentOutput(
                status='succeeded',
                plan_json_path=reused['plan_json_path'],
                pdf_path=reused.get('pdf_path'),
                reused=True,
            )
        else:
            plan_inp = PlanDocumentInput(
                pipeline_run_id=pipeline_run_id,
                session_id=session_id,
                form_state=form_state,
                delivery_id=delivery_id,
                allow_incomplete=bool((form_state or {}).get('_allow_incomplete')),
            )
            plan_out = await _run_with_timeout(
                run_plan_document(plan_inp, llm_json=llm_json, search_fn=search_fn),
                TIMEOUT_SEC['plan_document'],
                'plan_document',
            )

        if plan_out.status == 'failed':
            db.update_pipeline_run(
                pipeline_run_id,
                status='failed',
                current_skill='plan_document',
                error=plan_out.error or 'plan_document 失败',
            )
            return build_pipeline_detail(pipeline_run_id) or {}

        # ── F3 preview_images ────────────────────────────
        if _is_cancelled(pipeline_run_id):
            raise PipelineCancelled()

        db.update_pipeline_run(pipeline_run_id, current_skill='preview_images')
        images_inp = PreviewImagesInput(
            pipeline_run_id=pipeline_run_id,
            plan_json_path=plan_out.plan_json_path,
            image_count=3,
            quality='standard',
            allow_partial=True,
        )
        images_out = await _run_with_timeout(
            run_preview_images(images_inp, client=image_client, root=root),
            TIMEOUT_SEC['preview_images'],
            'preview_images',
        )

        # ── F4 preview_video ─────────────────────────────
        if _is_cancelled(pipeline_run_id):
            raise PipelineCancelled()

        db.update_pipeline_run(pipeline_run_id, current_skill='preview_video')
        image_dicts = [img.model_dump(mode='json') for img in images_out.images]
        if image_dicts:
            video_inp = PreviewVideoInput(
                pipeline_run_id=pipeline_run_id,
                plan_json_path=plan_out.plan_json_path,
                images=image_dicts,
                duration_sec=8,
                resolution='720P',
                source_angle='front',
            )
            video_out = await _run_with_timeout(
                run_preview_video(video_inp, client=video_client, root=root),
                TIMEOUT_SEC['preview_video'],
                'preview_video',
            )
        else:
            video_out = PreviewVideoOutput(
                status='failed',
                error='无可用预览图，跳过视频生成',
                warnings=['无可用预览图，跳过视频生成'],
            )

        # ── F5 final_package ─────────────────────────────
        if _is_cancelled(pipeline_run_id):
            raise PipelineCancelled()

        db.update_pipeline_run(pipeline_run_id, current_skill='final_package')
        final_inp = FinalPackageInput(
            pipeline_run_id=pipeline_run_id,
            session_id=session_id,
            form_state=form_state,
            plan_output=plan_out.model_dump(mode='json'),
            images_output=images_out.model_dump(mode='json'),
            video_output=video_out.model_dump(mode='json'),
        )

        def _run_final():
            return _run_final_package_tracked(
                pipeline_run_id,
                final_inp,
                root=root,
                readme_llm=readme_llm,
            )

        final_out = await _run_with_timeout(
            asyncio.to_thread(_run_final),
            TIMEOUT_SEC['final_package'],
            'final_package',
        )

        if final_out.status == 'failed':
            db.update_pipeline_run(
                pipeline_run_id,
                status='failed',
                current_skill='final_package',
                error=final_out.error or 'final_package 失败',
            )
        else:
            db.update_pipeline_run(
                pipeline_run_id,
                status=final_out.status,
                current_skill='final_package',
                error=None,
            )
        return build_pipeline_detail(pipeline_run_id) or {}

    except PipelineCancelled:
        db.update_pipeline_run(pipeline_run_id, status='cancelled', error='用户取消')
        return build_pipeline_detail(pipeline_run_id) or {}
    except TimeoutError as exc:
        current = (db.get_pipeline_run(pipeline_run_id) or {}).get('current_skill')
        db.update_pipeline_run(
            pipeline_run_id,
            status='failed',
            error=str(exc),
        )
        logger.warning('pipeline %s timeout at %s: %s', pipeline_run_id, current, exc)
        return build_pipeline_detail(pipeline_run_id) or {}
    except Exception as exc:
        logger.exception('pipeline %s failed', pipeline_run_id)
        db.update_pipeline_run(pipeline_run_id, status='failed', error=str(exc))
        return build_pipeline_detail(pipeline_run_id) or {}


async def retry_pipeline_skill(
    pipeline_run_id: str,
    skill: str,
    **kwargs,
) -> dict[str, Any]:
    """从指定 failed skill 起继续（不重跑更早已成功阶段）。"""
    if skill not in SKILL_ORDER:
        raise ValueError(f'未知 skill: {skill}')

    run = db.get_pipeline_run(pipeline_run_id)
    if run is None:
        raise ValueError(f'pipeline_run 不存在: {pipeline_run_id}')
    if run['status'] == 'running':
        raise RuntimeError('管线运行中，不能重试')

    status_map = db.latest_skill_status_map(pipeline_run_id)
    # 允许重试 failed / partial 的 skill；final_package 失败也可重试
    if status_map.get(skill) not in {'failed', 'partial'}:
        # 若整条 run failed 但该 skill 尚未跑过（上游失败导致），允许从该 skill 开始
        if status_map.get(skill) in {'succeeded', 'degraded', 'ready', 'ready_with_warnings'}:
            # 已成功：从下一个 failed 开始
            next_failed = None
            for s in SKILL_ORDER[SKILL_ORDER.index(skill):]:
                if status_map.get(s) in {'failed', 'partial', None, 'pending'}:
                    next_failed = s
                    break
            if next_failed is None:
                raise RuntimeError(f'{skill} 已成功且无后续失败 skill')
            skill = next_failed
        elif status_map.get(skill) in {None, 'pending', 'running'}:
            pass  # 允许首次执行该阶段

    db.update_pipeline_run(pipeline_run_id, status='running', current_skill=skill, error=None)
    return await run_pipeline_from_skill(pipeline_run_id, skill, **kwargs)


async def run_pipeline_from_skill(
    pipeline_run_id: str,
    start_skill: str,
    *,
    form_state: dict[str, Any] | None = None,
    llm_json=None,
    search_fn=None,
    image_client=None,
    video_client=None,
    readme_llm=None,
    artifact_root: Path | None = None,
) -> dict[str, Any]:
    """从 start_skill 开始执行后续阶段。"""
    if start_skill not in SKILL_ORDER:
        raise ValueError(f'未知 skill: {start_skill}')

    run = db.get_pipeline_run(pipeline_run_id)
    if run is None:
        raise ValueError(f'pipeline_run 不存在: {pipeline_run_id}')

    if form_state is None:
        form_state, _ = _load_session_context(run['session_id'])

    root = artifact_root or get_artifact_root()
    session_id = run['session_id']
    delivery_id = run.get('delivery_id')
    start_idx = SKILL_ORDER.index(start_skill)

    db.update_pipeline_run(pipeline_run_id, status='running', current_skill=start_skill)

    try:
        # 复用上游产物
        plan_out: PlanDocumentOutput
        if start_idx > 0:
            from pipeline.artifacts import try_reuse_plan

            reused = try_reuse_plan(pipeline_run_id, root)
            if reused is None:
                raise RuntimeError('缺少 plan.json，无法从中游重试；请从 plan_document 重试')
            plan_out = PlanDocumentOutput(
                status='succeeded',
                plan_json_path=reused['plan_json_path'],
                pdf_path=reused.get('pdf_path'),
                reused=True,
            )
        else:
            if _is_cancelled(pipeline_run_id):
                raise PipelineCancelled()
            db.update_pipeline_run(pipeline_run_id, current_skill='plan_document')
            plan_inp = PlanDocumentInput(
                pipeline_run_id=pipeline_run_id,
                session_id=session_id,
                form_state=form_state,
                delivery_id=delivery_id,
                allow_incomplete=bool((form_state or {}).get('_allow_incomplete')),
            )
            plan_out = await _run_with_timeout(
                run_plan_document(plan_inp, llm_json=llm_json, search_fn=search_fn),
                TIMEOUT_SEC['plan_document'],
                'plan_document',
            )
            if plan_out.status == 'failed':
                db.update_pipeline_run(
                    pipeline_run_id,
                    status='failed',
                    current_skill='plan_document',
                    error=plan_out.error or 'plan_document 失败',
                )
                return build_pipeline_detail(pipeline_run_id) or {}

        images_out: PreviewImagesOutput | None = None
        if start_idx <= SKILL_ORDER.index('preview_images'):
            if _is_cancelled(pipeline_run_id):
                raise PipelineCancelled()
            db.update_pipeline_run(pipeline_run_id, current_skill='preview_images')
            # force 生图：重试时用新 seed
            images_inp = PreviewImagesInput(
                pipeline_run_id=pipeline_run_id,
                plan_json_path=plan_out.plan_json_path,
                image_count=3,
                quality='standard',
                allow_partial=True,
                force=True,
            )
            images_out = await _run_with_timeout(
                run_preview_images(images_inp, client=image_client, root=root),
                TIMEOUT_SEC['preview_images'],
                'preview_images',
            )
        else:
            images_out = _load_images_output_from_disk(pipeline_run_id, plan_out.plan_json_path, root)

        video_out: PreviewVideoOutput | None = None
        if start_idx <= SKILL_ORDER.index('preview_video'):
            if _is_cancelled(pipeline_run_id):
                raise PipelineCancelled()
            db.update_pipeline_run(pipeline_run_id, current_skill='preview_video')
            image_dicts = [img.model_dump(mode='json') for img in (images_out.images if images_out else [])]
            if image_dicts:
                video_inp = PreviewVideoInput(
                    pipeline_run_id=pipeline_run_id,
                    plan_json_path=plan_out.plan_json_path,
                    images=image_dicts,
                    duration_sec=8,
                    resolution='720P',
                    source_angle='front',
                    force=True,
                )
                video_out = await _run_with_timeout(
                    run_preview_video(video_inp, client=video_client, root=root),
                    TIMEOUT_SEC['preview_video'],
                    'preview_video',
                )
            else:
                video_out = PreviewVideoOutput(
                    status='failed',
                    error='无可用预览图，跳过视频生成',
                )
        else:
            video_out = _load_video_output_from_disk(pipeline_run_id, root)

        if _is_cancelled(pipeline_run_id):
            raise PipelineCancelled()
        db.update_pipeline_run(pipeline_run_id, current_skill='final_package')
        final_inp = FinalPackageInput(
            pipeline_run_id=pipeline_run_id,
            session_id=session_id,
            form_state=form_state,
            plan_output=plan_out.model_dump(mode='json'),
            images_output=(images_out or PreviewImagesOutput(status='failed')).model_dump(mode='json'),
            video_output=(video_out or PreviewVideoOutput(status='failed')).model_dump(mode='json'),
        )

        def _run_final():
            return _run_final_package_tracked(
                pipeline_run_id,
                final_inp,
                root=root,
                readme_llm=readme_llm,
            )

        final_out = await _run_with_timeout(
            asyncio.to_thread(_run_final),
            TIMEOUT_SEC['final_package'],
            'final_package',
        )

        if final_out.status == 'failed':
            db.update_pipeline_run(
                pipeline_run_id,
                status='failed',
                current_skill='final_package',
                error=final_out.error or 'final_package 失败',
            )
        else:
            db.update_pipeline_run(
                pipeline_run_id,
                status=final_out.status,
                current_skill='final_package',
                error=None,
            )
        return build_pipeline_detail(pipeline_run_id) or {}
    except PipelineCancelled:
        db.update_pipeline_run(pipeline_run_id, status='cancelled', error='用户取消')
        return build_pipeline_detail(pipeline_run_id) or {}
    except Exception as exc:
        logger.exception('pipeline retry from %s failed', start_skill)
        db.update_pipeline_run(pipeline_run_id, status='failed', error=str(exc))
        return build_pipeline_detail(pipeline_run_id) or {}


def _load_images_output_from_disk(
    pipeline_run_id: str,
    plan_json_path: str,
    root: Path,
) -> PreviewImagesOutput:
    from media.dashscope_image import is_valid_png
    from pipeline.models import PreviewImageItem
    from pipeline.skills.preview_images import images_dir

    out_dir = images_dir(pipeline_run_id, root)
    items: list[PreviewImageItem] = []
    for angle in ('front', 'left', 'rear'):
        path = out_dir / f'preview_{angle}.png'
        if is_valid_png(path):
            items.append(
                PreviewImageItem(
                    angle=angle,
                    path=str(path),
                    width=0,
                    height=0,
                    sha256='',
                    model='',
                    cost_cny=0.0,
                    seed=None,
                )
            )
    if len(items) >= 3:
        status = 'succeeded'
    elif items:
        status = 'partial'
    else:
        status = 'failed'
    return PreviewImagesOutput(
        status=status,  # type: ignore[arg-type]
        images=items,
    )


def _load_video_output_from_disk(pipeline_run_id: str, root: Path) -> PreviewVideoOutput:
    from pipeline import store as pipeline_store

    existing = pipeline_store.find_latest_video_artifact(pipeline_run_id)
    if existing and pipeline_store.video_file_usable(existing['path']):
        meta = existing.get('meta') or {}
        return PreviewVideoOutput(
            status='succeeded',
            video_path=existing['path'],
            source_image=meta.get('source_image'),
            duration_sec=float(meta.get('duration_sec') or 0),
            resolution=str(meta.get('resolution') or ''),
            model=str(meta.get('model') or ''),
            sha256=str(existing.get('sha256') or ''),
            cost_cny=float(meta.get('cost_cny') or 0),
            reused=True,
        )
    return PreviewVideoOutput(status='failed', error='无已有视频产物')


def create_and_start_pipeline(
    *,
    session_id: str,
    user_id: int,
    delivery_id: int | None = None,
    **run_kwargs,
) -> str:
    """创建 pipeline_run 并后台启动。返回 run id。"""
    if db.count_active_pipeline_runs(user_id) >= 1:
        raise RuntimeError('已有进行中的方案生成，请等待完成后再试')

    run_id = db.create_pipeline_run(
        session_id=session_id,
        user_id=user_id,
        delivery_id=delivery_id,
        status='pending',
    )

    async def _bg():
        try:
            await run_pipeline(run_id, **run_kwargs)
        except Exception:
            logger.exception('background pipeline failed: %s', run_id)

    # 调用方负责 schedule；这里只创建
    return run_id
