"""F5 final_package — 交叉校验 + 说明 + 最终交付包。

幂等：重跑重新生成 README + manifest + zip；复用已有媒体文件；不调用生图/生视频。
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from pipeline.models import (
    FinalPackageInput,
    FinalPackageOutput,
    PlanDocumentOutput,
    PlanDraft,
    PreviewImagesOutput,
    PreviewVideoOutput,
    utc_now_iso,
)
from pipeline.packager import (
    build_equipment_xlsx,
    collect_manifest_files,
    copy_into_package,
    ensure_clean_dir,
    make_zip,
    write_json,
    write_text,
)
from pipeline.readme import ReadmeLLM, generate_readme
from pipeline.validate import run_validation

logger = logging.getLogger(__name__)

# LLM 写说明的粗略成本（元），写入 manifest.skills.final_package.cost_cny
README_LLM_COST_CNY = 0.02


def artifact_root() -> Path:
    """ARTIFACT_ROOT 环境变量，默认 backend/data/artifacts。"""
    env = os.getenv('ARTIFACT_ROOT')
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[1] / 'data' / 'artifacts'


def package_dir_for(pipeline_run_id: str, root: Path | None = None) -> Path:
    return (root or artifact_root()) / pipeline_run_id / 'package'


def _load_plan_json(path: str) -> PlanDraft:
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    return PlanDraft.model_validate(data)


def _brand_from(form_state: dict[str, Any], plan: PlanDraft) -> str:
    from pipeline.validate import extract_form_field

    brand = extract_form_field(form_state, 'customer.brand')
    if isinstance(brand, str) and brand.strip():
        return brand.strip()
    meta_brand = (plan.meta or {}).get('brand')
    if isinstance(meta_brand, str) and meta_brand.strip():
        return meta_brand.strip()
    return '直播间搭建'


def _sum_costs(
    plan_output: PlanDocumentOutput,
    images_output: PreviewImagesOutput,
    video_output: PreviewVideoOutput,
    final_cost: float,
) -> float:
    return round(
        plan_output.cost_cny
        + images_output.total_cost_cny
        + video_output.cost_cny
        + final_cost,
        6,
    )


def _failed_output(
    error: str,
    *,
    pipeline_run_id: str,
    session_id: str,
    skills: dict[str, Any],
    total_cost: float,
    warnings: list[str],
) -> FinalPackageOutput:
    manifest = {
        'pipeline_run_id': pipeline_run_id,
        'session_id': session_id,
        'generated_at': utc_now_iso(),
        'skills': skills,
        'files': [],
        'gaps': [],
        'total_cost_cny': total_cost,
        'warnings': warnings,
    }
    return FinalPackageOutput(
        status='failed',
        package_dir=None,
        zip_path=None,
        manifest=manifest,
        delivery_notes_md='',
        total_cost_cny=total_cost,
        warnings=warnings,
        error=error,
    )


def run_final_package(
    data: FinalPackageInput,
    *,
    artifact_root_override: Path | None = None,
    readme_llm: ReadmeLLM | None = None,
) -> FinalPackageOutput:
    """执行 F5。`readme_llm` 可注入；None 时用确定性模板。"""
    warnings: list[str] = []
    plan_output = PlanDocumentOutput.model_validate(data.plan_output)
    images_output = PreviewImagesOutput.model_validate(data.images_output)
    video_output = PreviewVideoOutput.model_validate(data.video_output)

    skills: dict[str, Any] = {
        'plan_document': {
            'status': plan_output.status,
            'cost_cny': plan_output.cost_cny,
        },
        'preview_images': {
            'status': images_output.status,
            'cost_cny': images_output.total_cost_cny,
            'angles': [img.angle for img in images_output.images],
        },
        'preview_video': {
            'status': video_output.status,
            'cost_cny': video_output.cost_cny,
        },
        'final_package': {
            'status': 'running',
            'cost_cny': 0.0,
        },
    }

    if plan_output.status == 'failed':
        skills['final_package'] = {'status': 'failed', 'cost_cny': 0.0}
        return _failed_output(
            plan_output.error or '上游方案文档失败，不打包',
            pipeline_run_id=data.pipeline_run_id,
            session_id=data.session_id,
            skills=skills,
            total_cost=_sum_costs(plan_output, images_output, video_output, 0.0),
            warnings=list(plan_output.warnings),
        )

    try:
        plan = _load_plan_json(plan_output.plan_json_path)
    except Exception as exc:
        skills['final_package'] = {'status': 'failed', 'cost_cny': 0.0}
        return _failed_output(
            f'无法读取 plan.json：{exc}',
            pipeline_run_id=data.pipeline_run_id,
            session_id=data.session_id,
            skills=skills,
            total_cost=_sum_costs(plan_output, images_output, video_output, 0.0),
            warnings=[],
        )

    # 若 plan.json 缺 scene_card，用 F2 output 兜底
    if not plan.scene_card.camera_angles and plan_output.scene_card:
        from pipeline.models import SceneCard

        plan.scene_card = SceneCard.model_validate(plan_output.scene_card)

    validation = run_validation(
        plan_output=plan_output,
        plan=plan,
        images_output=images_output,
        video_output=video_output,
        form_state=data.form_state,
        known_knowledge_ids=data.known_knowledge_ids,
    )

    if validation.has_error:
        skills['final_package'] = {'status': 'failed', 'cost_cny': 0.0}
        err = validation.errors[0].message
        return _failed_output(
            err,
            pipeline_run_id=data.pipeline_run_id,
            session_id=data.session_id,
            skills=skills,
            total_cost=_sum_costs(plan_output, images_output, video_output, 0.0),
            warnings=validation.warning_messages + list(plan_output.warnings),
        )

    package_dir = package_dir_for(data.pipeline_run_id, artifact_root_override)
    # 重跑：清空后重建 README/manifest/zip；媒体从上游产物拷贝（复用，不重新生成）
    ensure_clean_dir(package_dir, force=True)
    (package_dir / 'docs').mkdir(parents=True, exist_ok=True)
    (package_dir / 'images').mkdir(parents=True, exist_ok=True)
    (package_dir / 'video').mkdir(parents=True, exist_ok=True)

    # 1) docs: plan.json + plan.pdf（或降级 docx）
    copy_into_package(Path(plan_output.plan_json_path), package_dir, 'docs/plan.json')
    has_plan_pdf = False
    if plan_output.pdf_path and Path(plan_output.pdf_path).is_file():
        copy_into_package(Path(plan_output.pdf_path), package_dir, 'docs/plan.pdf')
        has_plan_pdf = True
    else:
        docx_src = Path(plan_output.plan_json_path).parent / 'plan.docx'
        if docx_src.is_file():
            copy_into_package(docx_src, package_dir, 'docs/plan.docx')

    # 2) images
    present_images: list[dict[str, str]] = []
    # 重新从 validation 过滤真实存在的图（validate_images 已做存在性检查）
    scene_angles = list(plan.scene_card.camera_angles or ['front', 'left', 'rear'])
    present_angles: set[str] = set()
    for img in images_output.images:
        src = Path(img.path)
        if not src.is_file() or src.stat().st_size <= 0:
            continue
        dest_name = f'preview_{img.angle}.png'
        copy_into_package(src, package_dir, f'images/{dest_name}')
        present_images.append({'angle': img.angle, 'path': f'images/{dest_name}'})
        present_angles.add(img.angle)
    for angle in scene_angles:
        if angle not in present_angles and f'missing_angle:{angle}' not in validation.gaps:
            validation.add_gap(f'missing_angle:{angle}')

    # 3) video
    video_included = False
    if video_output.status == 'succeeded' and video_output.video_path:
        vsrc = Path(video_output.video_path)
        if vsrc.is_file() and vsrc.stat().st_size > 0:
            copy_into_package(vsrc, package_dir, 'video/preview.mp4')
            video_included = True

    # 4) optional equipment xlsx
    has_equipment_xlsx = False
    if data.include_equipment_xlsx and validation.equipment_list:
        build_equipment_xlsx(
            package_dir,
            validation.equipment_list,
            _brand_from(data.form_state, plan),
        )
        has_equipment_xlsx = True

    # 5) README
    brand = _brand_from(data.form_state, plan)
    delivery_notes_md = generate_readme(
        brand=brand,
        summary=plan.summary,
        plan=plan,
        equipment_list=validation.equipment_list,
        present_images=present_images,
        video_included=video_included,
        validation=validation,
        has_plan_pdf=has_plan_pdf,
        has_equipment_xlsx=has_equipment_xlsx,
        llm=readme_llm,
    )
    write_text(package_dir / 'README.md', delivery_notes_md)

    final_cost = README_LLM_COST_CNY if readme_llm else 0.0
    warnings = validation.warning_messages + list(plan_output.warnings) + list(images_output.warnings) + list(video_output.warnings)
    # 去重保序
    seen: set[str] = set()
    uniq_warnings: list[str] = []
    for w in warnings:
        if w not in seen:
            seen.add(w)
            uniq_warnings.append(w)

    status = 'ready_with_warnings' if uniq_warnings or validation.gaps else 'ready'
    skills['final_package'] = {
        'status': status,
        'cost_cny': final_cost,
    }

    # 6) manifest（先写占位再回填 files，保证 files 含 README 等全部产物）
    files = collect_manifest_files(package_dir)
    manifest = {
        'pipeline_run_id': data.pipeline_run_id,
        'session_id': data.session_id,
        'generated_at': utc_now_iso(),
        'skills': skills,
        'files': [f.model_dump() for f in files],
        'gaps': list(validation.gaps),
        'total_cost_cny': _sum_costs(plan_output, images_output, video_output, final_cost),
        'warnings': uniq_warnings,
    }
    write_json(package_dir / 'manifest.json', manifest)

    # 7) zip
    zip_path: Path | None = None
    if data.include_zip:
        zip_path = make_zip(package_dir)

    return FinalPackageOutput(
        status=status,
        package_dir=str(package_dir),
        zip_path=str(zip_path) if zip_path else None,
        manifest=manifest,
        delivery_notes_md=delivery_notes_md,
        total_cost_cny=manifest['total_cost_cny'],
        warnings=uniq_warnings,
        error=None,
    )
