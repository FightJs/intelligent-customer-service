"""F2 Skill 主流程：Normalize → Decompose → Retrieve → Compose → Validate → Render → Persist。"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from knowledge.models import KnowledgeHit
from knowledge.search import hybrid_search as default_search
from pipeline.artifacts import persist_plan_artifacts, try_reuse_plan
from pipeline.llm_calls import (
    build_compose_prompt,
    build_decompose_prompt,
    call_llm_json,
    estimate_cost,
    fallback_intents,
    parse_compose_payload,
    parse_decompose_payload,
)
from pipeline.models import (
    LLMJsonFn,
    PlanDocumentInput,
    PlanDocumentOutput,
    PlanDraft,
    RequirementBrief,
    RetrievalIntent,
)
from pipeline.normalize import normalize_form_state
from pipeline.templates_plan import build_template_plan
from pipeline.validate import validate_plan
from store import db

logger = logging.getLogger(__name__)

DEFAULT_INTENT_LIMIT = 6
HIT_LIMIT_PER_INTENT = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _default_search_fn(intent: RetrievalIntent) -> list[KnowledgeHit]:
    # hybrid_search 为同步；封装成 async 以统一注入点
    response = default_search(
        intent.collection,
        intent.query,
        industry=intent.filters.get('industry') if isinstance(intent.filters.get('industry'), str) else None,
        room_size=intent.filters.get('room_size') if isinstance(intent.filters.get('room_size'), str) else None,
        budget_level=intent.filters.get('budget_level') if isinstance(intent.filters.get('budget_level'), str) else None,
        category=intent.filters.get('category') if isinstance(intent.filters.get('category'), str) else None,
        limit=HIT_LIMIT_PER_INTENT,
    )
    return response.hits


async def _retrieve(
    intents: list[RetrievalIntent],
    search_fn,
) -> tuple[list[KnowledgeHit], bool]:
    """对各意图检索并去重。全部无命中视为 knowledge_degraded。"""
    hits: list[KnowledgeHit] = []
    seen: set[tuple[str, int]] = set()
    for intent in intents[:DEFAULT_INTENT_LIMIT]:
        try:
            result = await search_fn(intent)
        except Exception:
            logger.warning('retrieve failed', exc_info=True)
            continue
        for hit in result or []:
            key = (hit.collection, hit.id)
            if key in seen:
                continue
            seen.add(key)
            hits.append(hit)
    return hits, not hits


async def _decompose(
    brief: RequirementBrief,
    llm_json: LLMJsonFn,
    cost_box: dict[str, float],
    warnings: list[str],
) -> list[RetrievalIntent]:
    system, user = build_decompose_prompt(brief)
    try:
        payload = await llm_json(system, user)
        cost_box['cost'] += estimate_cost(len(system) + len(user), len(str(payload)))
        intents = parse_decompose_payload(payload)
        if intents:
            return intents
        warnings.append('LLM 检索意图为空，使用默认意图')
    except Exception as exc:
        logger.warning('decompose failed: %s', exc)
        warnings.append(f'检索意图拆解失败，使用默认意图：{exc}')
    return [
        RetrievalIntent(
            collection=item.collection,
            query=item.query,
            filters=item.filters,
        )
        for item in fallback_intents(brief)
    ]


async def _compose(
    brief: RequirementBrief,
    hits: list[KnowledgeHit],
    llm_json: LLMJsonFn,
    cost_box: dict[str, float],
    pipeline_run_id: str,
    warnings: list[str],
) -> PlanDraft:
    system, user = build_compose_prompt(brief, hits)
    try:
        payload = await llm_json(system, user)
        cost_box['cost'] += estimate_cost(len(system) + len(user), len(str(payload)))
        draft = parse_compose_payload(payload)
    except Exception as exc:
        logger.warning('compose failed: %s', exc)
        raise RuntimeError(f'方案组合失败：{exc}') from exc

    draft.meta.setdefault('brand', brief.brand)
    draft.meta.setdefault('industry', brief.industry)
    draft.meta.setdefault('room_size', brief.room_size)
    draft.meta.setdefault('budget_total', brief.budget_total)
    draft.meta['generated_at'] = draft.meta.get('generated_at') or _now_iso()
    draft.meta['pipeline_run_id'] = pipeline_run_id
    draft.meta['completeness'] = brief.completeness
    draft.meta['knowledge_refs'] = [
        {'collection': hit.collection, 'id': hit.id} for hit in hits
    ]
    status_flags = list(draft.meta.get('status_flags') or [])
    if hits:
        status_flags = [flag for flag in status_flags if flag != 'knowledge_unavailable']
    draft.meta['status_flags'] = status_flags

    # 建议：已有设备保留在清单并标注
    owned_keys = {
        (item.type.strip(), item.model.strip())
        for item in brief.existing_equipment
        if item.type or item.model
    }
    if owned_keys:
        for item in draft.equipment_list:
            name = item.name.strip()
            model = item.model.strip()
            for owned_type, owned_model in owned_keys:
                if name == owned_type or model == owned_model:
                    item.already_owned = True
    return draft


def _mark_existing_equipment(draft: PlanDraft, brief: RequirementBrief) -> None:
    if not brief.existing_equipment:
        return
    owned_types = {item.type.strip() for item in brief.existing_equipment if item.type}
    owned_models = {item.model.strip() for item in brief.existing_equipment if item.model}
    for item in draft.equipment_list:
        if item.name.strip() in owned_types or item.model.strip() in owned_models:
            item.already_owned = True


async def run_plan_document(
    inp: PlanDocumentInput,
    *,
    llm_json: LLMJsonFn | None = None,
    search_fn=None,
) -> PlanDocumentOutput:
    """执行 plan_document skill。"""
    llm = llm_json or call_llm_json
    search = search_fn or _default_search_fn
    cost_box = {'cost': 0.0}
    warnings: list[str] = []

    db.start_skill_run(
        pipeline_run_id=inp.pipeline_run_id,
        skill='plan_document',
        input_json=inp.model_dump(mode='json'),
    )

    try:
        if not inp.force:
            reused = try_reuse_plan(inp.pipeline_run_id)
            if reused is not None:
                brief = normalize_form_state(inp.form_state)
                plan = reused['plan']
                db.finish_skill_run_latest(
                    pipeline_run_id=inp.pipeline_run_id,
                    skill='plan_document',
                    status='succeeded',
                    output_json={
                        'plan_json_path': reused['plan_json_path'],
                        'pdf_path': reused.get('pdf_path'),
                        'reused': True,
                    },
                    cost_cny=0.0,
                )
                return PlanDocumentOutput(
                    status='succeeded',
                    plan_json_path=reused['plan_json_path'],
                    pdf_path=reused.get('pdf_path'),
                    requirement_brief=brief.model_dump(),
                    knowledge_hits=(plan.get('meta') or {}).get('knowledge_refs') or [],
                    scene_card=plan.get('scene_card') or {},
                    cost_cny=0.0,
                    warnings=['复用已有 plan.json，未重复计费'],
                    reused=True,
                )

        brief = normalize_form_state(inp.form_state)
        if brief.missing_core_fields and not inp.allow_incomplete:
            error = f'核心需求缺失：{", ".join(brief.missing_core_fields)}'
            db.finish_skill_run_latest(
                pipeline_run_id=inp.pipeline_run_id,
                skill='plan_document',
                status='failed',
                output_json={'error': error},
                cost_cny=cost_box['cost'],
                error=error,
            )
            return PlanDocumentOutput(
                status='failed',
                requirement_brief=brief.model_dump(),
                cost_cny=cost_box['cost'],
                warnings=warnings,
                error=error,
            )

        incomplete = bool(brief.missing_core_fields)
        if incomplete:
            warnings.append('需求信息不完整，继续生成（allow_incomplete）')

        intents = await _decompose(brief, llm, cost_box, warnings)
        hits, knowledge_degraded = await _retrieve(intents, search)
        if knowledge_degraded:
            warnings.append('知识库不可用或无命中，使用通用模板方案')

        if knowledge_degraded or not hits:
            draft = build_template_plan(brief)
            draft.meta['pipeline_run_id'] = inp.pipeline_run_id
            draft.meta['generated_at'] = _now_iso()
            draft.meta['completeness'] = brief.completeness
            draft.meta['knowledge_refs'] = []
            status_flags = list(draft.meta.get('status_flags') or [])
            if 'knowledge_unavailable' not in status_flags:
                status_flags.append('knowledge_unavailable')
            draft.meta['status_flags'] = status_flags
            skill_status = 'degraded'
        else:
            draft = await _compose(brief, hits, llm, cost_box, inp.pipeline_run_id, warnings)
            skill_status = 'succeeded'

        _mark_existing_equipment(draft, brief)
        validate_warnings, hard_errors = validate_plan(draft, brief)
        warnings.extend(validate_warnings)
        if hard_errors:
            error = '；'.join(hard_errors)
            db.finish_skill_run_latest(
                pipeline_run_id=inp.pipeline_run_id,
                skill='plan_document',
                status='failed',
                output_json={'error': error, 'warnings': warnings},
                cost_cny=cost_box['cost'],
                error=error,
            )
            return PlanDocumentOutput(
                status='failed',
                requirement_brief=brief.model_dump(),
                knowledge_hits=[hit.model_dump() for hit in hits],
                cost_cny=cost_box['cost'],
                warnings=warnings,
                error=error,
            )

        from delivery.pdf import render_plan_document

        plan_dict = draft.model_dump(mode='json')
        pdf_bytes, word_bytes, render_warnings = render_plan_document(
            plan_dict,
            brief.model_dump(),
            incomplete=incomplete,
            knowledge_degraded=knowledge_degraded,
        )
        warnings.extend(render_warnings)

        plan_json_path, pdf_path = persist_plan_artifacts(
            inp.pipeline_run_id,
            plan_dict,
            pdf_bytes=pdf_bytes,
            word_bytes=word_bytes,
        )

        output_payload = {
            'plan_json_path': plan_json_path,
            'pdf_path': pdf_path,
            'warnings': warnings,
            'knowledge_degraded': knowledge_degraded,
            'incomplete': incomplete,
        }
        db.finish_skill_run_latest(
            pipeline_run_id=inp.pipeline_run_id,
            skill='plan_document',
            status=skill_status,
            output_json=output_payload,
            cost_cny=cost_box['cost'],
        )

        return PlanDocumentOutput(
            status=skill_status,  # type: ignore[arg-type]
            plan_json_path=plan_json_path,
            pdf_path=pdf_path,
            requirement_brief=brief.model_dump(),
            knowledge_hits=[hit.model_dump() for hit in hits],
            scene_card=draft.scene_card.model_dump(),
            cost_cny=cost_box['cost'],
            warnings=warnings,
            error=None,
        )
    except Exception as exc:
        logger.exception('plan_document failed')
        db.finish_skill_run_latest(
            pipeline_run_id=inp.pipeline_run_id,
            skill='plan_document',
            status='failed',
            output_json={'error': str(exc), 'warnings': warnings},
            cost_cny=cost_box['cost'],
            error=str(exc),
        )
        return PlanDocumentOutput(
            status='failed',
            requirement_brief={},
            cost_cny=cost_box['cost'],
            warnings=warnings,
            error=str(exc),
        )
