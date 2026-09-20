"""F2 plan_document Skill 测试：mock LLM + mock 检索。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import store.db as db
from knowledge.models import KnowledgeHit
from pipeline.models import PlanDocumentInput
from pipeline.normalize import normalize_form_state
from pipeline.plan_document import run_plan_document
from pipeline.validate import validate_plan
from survey.state import create_initial_state, to_dict


def _fill_core_fields(state) -> None:
    state.sections['customer'].fields['brand'].value = '云裳'
    state.sections['industry'].fields['category'].value = 'women'
    state.sections['industry'].fields['subcategory'].value = '高端香云纱女装'
    state.sections['industry'].fields['price_band'].value = 'high'
    state.sections['industry'].fields['positioning'].value = 'mid-high'
    state.sections['industry'].fields['live_type'].value = 'brand'
    state.sections['venue'].fields['area'].value = '20-30'
    state.sections['venue'].fields['window'].value = 'coverable'
    state.sections['venue'].fields['window_pos'].value = 'right'
    state.sections['venue'].fields['renovation'].value = 'minor'
    state.sections['budget'].fields['total'].value = '3-5w'
    state.sections['budget'].fields['equipment'].value = '1-2w'
    state.sections['budget'].fields['decor'].value = '5k-1w'
    state.sections['budget'].fields['flex'].value = 'some'
    state.sections['budget'].fields['has_existing'].value = 'yes'
    state.sections['product'].fields['main'].value = '连衣裙'
    state.sections['product'].fields['keywords'].value = '国风、高端、雅致'
    state.sections['product'].fields['size_cat'].value = 'medium'
    state.sections['host'].fields['count'].value = '1'
    state.sections['host'].fields['movement'].value = 'occasional'
    state.sections['equipment'].fields['inventory'].value = [
        {'type': '相机', 'model': 'Sony A7M4', 'qty': '1'},
    ]
    state.sections['goal'].fields['core'].value = 'new'
    state.sections['goal'].fields['focus'].value = ['premium-look', 'product-quality']
    state.sections['goal'].fields['need_3d'].value = 'no'
    state.sections['goal'].fields['deadline'].value = '2w'


def _form_state() -> dict:
    state = create_initial_state()
    _fill_core_fields(state)
    return to_dict(state)


def _sample_plan_payload() -> dict:
    return {
        'summary': '云裳高端女装 20-30㎡ 品牌自播间高级感搭建方案',
        'layout': {
            'zones': [
                {'name': '主播区', 'notes': '单主播，偶尔站起，预留小幅活动空间'},
                {'name': '商品展示区', 'notes': '连衣裙全身/半身切换展示'},
                {'name': '背景区', 'notes': '国风层次背景，控制logo入画'},
            ],
            'lighting_plan': '三点布光：COB主灯×2 + 发丝灯，色温4000K。',
            'camera_plan': '主机位正面半身，副机位左侧45°。',
            'background_plan': '浅色纹理背景 + 木质展示架。',
        },
        'equipment_list': [
            {
                'knowledge_id': 1001,
                'category': '灯光',
                'name': '爱图仕 300D II',
                'model': '300D II',
                'brand': 'Aputure',
                'qty': 2,
                'unit_price_band': 'high',
                'reason': '适配 20-30㎡ 中高客单女装主光',
                'is_custom': False,
            },
            {
                'knowledge_id': None,
                'category': '相机',
                'name': '相机',
                'model': 'Sony A7M4',
                'brand': 'Sony',
                'qty': 1,
                'unit_price_band': 'high',
                'reason': '客户已有主机位',
                'is_custom': True,
            },
        ],
        'package_tiers': [
            {
                'tier': '性价比',
                'total_range': '2.8-3.2w',
                'items': [{'name': 'COB主灯', 'qty': 1}],
            },
            {
                'tier': '进阶',
                'total_range': '3.5-4.2w',
                'items': [{'name': 'COB主灯', 'qty': 2}],
            },
            {
                'tier': '高配',
                'total_range': '4.5-5.0w',
                'items': [{'name': '全画幅套装', 'qty': 1}],
            },
        ],
        'setup_steps': [
            '第1步：遮光与动线确认。',
            '第2步：功能分区与支架点位。',
            '第3步：三点布光调试。',
            '第4步：相机链路校准。',
            '第5步：试播验收。',
        ],
        'risks': ['窗户在主播右侧需遮光'],
        'scene_card': {
            'room_size_band': 'medium',
            'style_keywords': ['国风', '高端', '雅致'],
            'color_palette': ['#f5f0e8', '#2c2c2c', '#c4a574'],
            'color_temp': '4000K',
            'furniture': ['主播桌', '展示架'],
            'lighting_fixtures': ['COB主灯×2', '柔光箱×2'],
            'product_category': '女装',
            'camera_angles': ['front', 'left', 'rear'],
            'forbidden': ['文字水印', '品牌logo'],
        },
    }


@pytest.fixture
def artifact_root(tmp_path, monkeypatch):
    root = tmp_path / 'artifacts'
    monkeypatch.setenv('ARTIFACT_ROOT', str(root))
    return root


@pytest.fixture
def reset_knowledge_store():
    from knowledge.store import set_store

    set_store(None)
    yield
    set_store(None)


async def _mock_llm(system: str, user: str) -> dict:
    if '检索意图' in system or '检索策略' in system:
        return [
            {
                'collection': 'setup_schemes',
                'query': '女装 20㎡ 中高客单 品牌自播 搭建方案',
                'filters': {'industry': 'women', 'room_size': 'medium'},
            },
            {
                'collection': 'equipment_specs',
                'query': '三点布光 COB 常亮灯 服装类',
                'filters': {'category': '灯光', 'industry': 'women'},
            },
            {
                'collection': 'vertical_knowledge',
                'query': '女装直播间 背景层次 商品质感',
                'filters': {'industry': 'women', 'scene': '背景'},
            },
        ]
    return _sample_plan_payload()


async def _mock_search(intent):
    return [
        KnowledgeHit(
            collection=intent.collection,
            id=1001 if intent.collection == 'equipment_specs' else 2001,
            score=0.9,
            payload={
                'name': '爱图仕 300D II',
                'category': '灯光',
                'industry': 'women',
                'room_size': 'medium',
                'text': '女装直播间 COB 常亮灯 三点布光',
            },
        )
    ]


def test_normalize_form_state_maps_core_fields():
    brief = normalize_form_state(_form_state())
    assert brief.brand == '云裳'
    assert brief.industry == 'women'
    assert brief.room_size == 'medium'
    assert brief.area_band == '20-30'
    assert brief.budget_total == '3-5w'
    assert brief.product_keywords == ['国风', '高端', '雅致']
    assert brief.goal_focus == ['premium-look', 'product-quality']
    assert brief.existing_equipment[0].model == 'Sony A7M4'
    assert brief.missing_core_fields == []
    assert brief.completeness == 1.0


def test_template_plan_has_realistic_models_and_channels():
    """模板方案应含具体型号、必买项、参数、租赁渠道与垂类要点。"""
    from pipeline.templates_plan import build_template_plan

    brief = normalize_form_state(_form_state())
    plan = build_template_plan(brief)

    models = [item.model for item in plan.equipment_list if item.model]
    assert any('Aputure' in m or '爱图仕' in m or '200d' in m for m in models)
    assert any(item.must_buy for item in plan.equipment_list)
    assert all(item.specs for item in plan.equipment_list if item.must_buy)
    assert plan.must_buy_list
    assert plan.rental_channels
    assert plan.vertical_notes
    assert plan.meta.get('layout_scale')
    assert len(plan.package_tiers) == 3
    assert plan.package_tiers[0].items[0].model or plan.package_tiers[0].items[0].name


def test_normalize_incomplete_reports_missing(artifact_root):
    state = create_initial_state()
    brief = normalize_form_state(to_dict(state))
    assert 'customer.brand' in brief.missing_core_fields
    assert brief.completeness < 1.0


async def test_run_plan_document_success(artifact_root, reset_knowledge_store):
    run_id = 'run-success-001'
    inp = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=_form_state(),
    )
    output = await run_plan_document(inp, llm_json=_mock_llm, search_fn=_mock_search)

    assert output.status == 'succeeded'
    assert output.error is None
    assert Path(output.plan_json_path).exists()
    assert output.scene_card['style_keywords'] == ['国风', '高端', '雅致']

    plan = json.loads(Path(output.plan_json_path).read_text(encoding='utf-8'))
    assert plan['summary']
    assert len(plan['setup_steps']) >= 3
    assert len(plan['package_tiers']) == 3
    assert plan['equipment_list'][0]['knowledge_id'] == 1001
    # 已有设备应被标注
    owned = [item for item in plan['equipment_list'] if item.get('already_owned')]
    assert owned and owned[0]['model'] == 'Sony A7M4'
    # scene_card 完整
    assert plan['scene_card']['camera_angles'] == ['front', 'left', 'rear']

    # 有文档产物（pdf 或 word 降级）
    docs_dir = Path(output.plan_json_path).parent
    assert (docs_dir / 'plan.pdf').exists() or (docs_dir / 'plan.docx').exists()
    if output.pdf_path:
        assert Path(output.pdf_path).exists()

    runs = db.list_skill_runs(run_id)
    assert runs and runs[-1]['status'] == 'succeeded'


async def test_run_plan_document_idempotent_reuse(artifact_root, reset_knowledge_store):
    run_id = 'run-reuse-001'
    inp = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=_form_state(),
    )
    first = await run_plan_document(inp, llm_json=_mock_llm, search_fn=_mock_search)
    assert first.status in {'succeeded', 'degraded'}
    assert first.reused is False

    second = await run_plan_document(inp, llm_json=_mock_llm, search_fn=_mock_search)
    assert second.status == 'succeeded'
    assert second.reused is True
    assert second.cost_cny == 0.0
    assert second.plan_json_path == first.plan_json_path


async def test_run_plan_document_degraded_when_knowledge_unavailable(
    artifact_root,
    reset_knowledge_store,
):
    async def empty_search(intent):
        return []

    run_id = 'run-degraded-001'
    inp = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=_form_state(),
    )
    output = await run_plan_document(inp, llm_json=_mock_llm, search_fn=empty_search)

    assert output.status == 'degraded'
    assert Path(output.plan_json_path).exists()
    plan = json.loads(Path(output.plan_json_path).read_text(encoding='utf-8'))
    assert 'knowledge_unavailable' in plan['meta']['status_flags']
    assert plan['meta']['knowledge_refs'] == []
    assert len(plan['setup_steps']) >= 3
    assert any('知识库' in w for w in output.warnings)


async def test_run_plan_document_default_search_degraded(
    artifact_root,
    reset_knowledge_store,
):
    """检索无命中时走模板方案（degraded）。"""
    from knowledge.search import hybrid_search

    response = hybrid_search('equipment_specs', '女装 三点布光')
    # 未注入 store：可能 degraded 空结果，或因默认向量库不可达而 degraded
    assert response.degraded is True or not response.hits

    run_id = 'run-default-search-001'
    inp = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=_form_state(),
    )
    output = await run_plan_document(inp, llm_json=_mock_llm, search_fn=empty_hits)
    assert output.status == 'degraded'


async def test_core_fields_missing_fails_without_allow_incomplete(
    artifact_root,
    reset_knowledge_store,
):
    run_id = 'run-incomplete-001'
    inp = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=to_dict(create_initial_state()),
        allow_incomplete=False,
    )
    output = await run_plan_document(inp, llm_json=_mock_llm, search_fn=_mock_search)
    assert output.status == 'failed'
    assert '核心需求缺失' in (output.error or '')


async def test_allow_incomplete_continues(artifact_root, reset_knowledge_store):
    run_id = 'run-incomplete-002'
    inp = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=to_dict(create_initial_state()),
        allow_incomplete=True,
    )
    output = await run_plan_document(inp, llm_json=_mock_llm, search_fn=empty_hits)
    assert output.status in {'succeeded', 'degraded'}
    assert any('不完整' in w for w in output.warnings)


async def empty_hits(intent):
    return []


async def test_llm_compose_failure_returns_failed(artifact_root, reset_knowledge_store):
    calls = {'n': 0}

    async def flaky_llm(system: str, user: str) -> dict:
        if '检索意图' in system or '检索策略' in system:
            return [
                {
                    'collection': 'equipment_specs',
                    'query': '女装 灯光',
                    'filters': {'industry': 'women'},
                }
            ]
        calls['n'] += 1
        raise RuntimeError('compose boom')

    run_id = 'run-llm-fail-001'
    inp = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=_form_state(),
    )
    output = await run_plan_document(inp, llm_json=flaky_llm, search_fn=_mock_search)
    assert output.status == 'failed'
    assert '方案组合失败' in (output.error or '')


def test_validate_rejects_short_setup_steps():
    from pipeline.models import LayoutPlan, LayoutZone, PlanDraft, RequirementBrief

    draft = PlanDraft(
        summary='ok',
        layout=LayoutPlan(zones=[LayoutZone(name='主播区', notes='x')], lighting_plan='三点'),
        setup_steps=['第1步', '第2步'],
    )
    brief = RequirementBrief(budget_total='3-5w')
    warnings, errors = validate_plan(draft, brief)
    assert any('setup_steps' in e for e in errors)


def test_validate_drops_equipment_without_knowledge_id_or_custom():
    from pipeline.models import EquipmentItem, LayoutPlan, LayoutZone, PlanDraft, RequirementBrief

    draft = PlanDraft(
        summary='ok',
        layout=LayoutPlan(zones=[LayoutZone(name='主播区', notes='x')], lighting_plan='三点'),
        equipment_list=[
            EquipmentItem(category='灯光', name='幽灵灯', knowledge_id=None, is_custom=False),
            EquipmentItem(category='灯光', name='COB', knowledge_id=9, is_custom=False),
            EquipmentItem(category='背景', name='定制背景', knowledge_id=None, is_custom=True),
        ],
        setup_steps=['1', '2', '3'],
    )
    warnings, errors = validate_plan(draft, RequirementBrief())
    assert errors == []
    assert len(draft.equipment_list) == 2
    assert any('幽灵灯' in w for w in warnings)


def test_validate_budget_out_of_range_warns():
    from pipeline.models import (
        LayoutPlan,
        LayoutZone,
        PackageItem,
        PackageTier,
        PlanDraft,
        RequirementBrief,
    )

    draft = PlanDraft(
        summary='ok',
        layout=LayoutPlan(zones=[LayoutZone(name='主播区', notes='x')], lighting_plan='三点'),
        package_tiers=[
            PackageTier(
                tier='性价比',
                total_range='1.0-1.2w',
                items=[PackageItem(name='灯', qty=1)],
            ),
            PackageTier(
                tier='进阶',
                total_range='2.0-2.2w',
                items=[PackageItem(name='灯', qty=2)],
            ),
            PackageTier(
                tier='高配',
                total_range='3.0-3.2w',
                items=[PackageItem(name='套装', qty=1)],
            ),
        ],
        setup_steps=['1', '2', '3'],
    )
    brief = RequirementBrief(budget_total='3-5w', budget_flex='tight')
    warnings, errors = validate_plan(draft, brief)
    assert errors == []
    assert any('偏差' in w for w in warnings)


async def test_force_regenerates(artifact_root, reset_knowledge_store):
    run_id = 'run-force-001'
    inp = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=_form_state(),
    )
    first = await run_plan_document(inp, llm_json=_mock_llm, search_fn=_mock_search)
    assert first.status == 'succeeded'

    forced = PlanDocumentInput(
        pipeline_run_id=run_id,
        session_id='sess1',
        form_state=_form_state(),
        force=True,
    )
    second = await run_plan_document(forced, llm_json=_mock_llm, search_fn=_mock_search)
    assert second.reused is False
    assert second.status == 'succeeded'
