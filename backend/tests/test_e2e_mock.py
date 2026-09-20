"""剧本 A — CI 全 Mock 端到端：F2→F3→F4→F5 串跑。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

import store.db as db
from knowledge.models import KnowledgeHit
from media.dashscope_image import PNG_MAGIC
from pipeline.models import PreviewImagesInput, PreviewVideoInput
from pipeline.orchestrator import run_pipeline
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
                {'name': '主播区', 'notes': '单主播'},
                {'name': '商品展示区', 'notes': '连衣裙展示'},
                {'name': '背景区', 'notes': '国风背景'},
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
                'reason': '适配中高客单女装主光',
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
            {'tier': '性价比', 'total_range': '2.8-3.2w', 'items': [{'name': 'COB主灯', 'qty': 1}]},
            {'tier': '进阶', 'total_range': '3.5-4.2w', 'items': [{'name': 'COB主灯', 'qty': 2}]},
            {'tier': '高配', 'total_range': '4.5-5.0w', 'items': [{'name': '全画幅套装', 'qty': 1}]},
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


class FakeImageClient:
    def __init__(self):
        self.submits = 0

    async def submit_t2i(self, *, model, prompt, seed=None, size='1280*720', n=1) -> str:
        self.submits += 1
        return f'img-{self.submits}'

    async def wait_task(self, task_id: str, *, timeout_sec=None):
        class _R:
            status = 'SUCCEEDED'
            image_urls = [f'https://example.com/{task_id}.png']
            seed = 7
            message = None

        return _R()

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(PNG_MAGIC + b'0' * 4096)
        return dest


class FakeVideoClient:
    def __init__(self, video_size: int = 120_000):
        self.video_size = video_size
        self.submits = 0

    async def submit_i2v(self, *, model, prompt, image_path, duration_sec, resolution) -> str:
        self.submits += 1
        return f'vid-{self.submits}'

    async def wait_task(self, task_id: str, *, timeout_sec=None):
        class _R:
            status = 'SUCCEEDED'
            video_url = 'https://example.com/preview.mp4'
            message = None

        return _R()

    async def download(self, url: str, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'0' * self.video_size)
        return dest


@pytest.fixture
def artifact_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / 'artifacts'
    monkeypatch.setenv('ARTIFACT_ROOT', str(root))
    return root


async def test_e2e_mock_full_pipeline(artifact_root: Path):
    """剧本 A：全 mock 成功 → ready / ready_with_warnings + 包内产物齐全。"""
    user_id = db.create_user(f'e2e_full_{id(object())}', 'hash', role='user')
    session_id = db.create_session(user_id, _form_state())
    run_id = db.create_pipeline_run(session_id=session_id, user_id=user_id)

    detail = await run_pipeline(
        run_id,
        form_state=_form_state(),
        llm_json=_mock_llm,
        search_fn=_mock_search,
        image_client=FakeImageClient(),
        video_client=FakeVideoClient(),
        artifact_root=artifact_root,
    )

    assert detail['raw_status'] in {'ready', 'ready_with_warnings'}
    assert detail['status'] in {'ready', 'partial'}  # partial 仅当有 warning 映射
    assert detail['skills']['plan'] == 'succeeded'
    assert detail['skills']['images'] == 'succeeded'
    assert detail['skills']['video'] == 'succeeded'
    assert detail['skills']['package'] == 'succeeded'

    package_dir = artifact_root / run_id / 'package'
    assert (package_dir / 'docs' / 'plan.json').is_file()
    # WeasyPrint 可用时为 pdf，否则降级 docx（F2-I03）
    assert (package_dir / 'docs' / 'plan.pdf').is_file() or (package_dir / 'docs' / 'plan.docx').is_file()
    assert (package_dir / 'images' / 'preview_front.png').is_file()
    assert (package_dir / 'images' / 'preview_left.png').is_file()
    assert (package_dir / 'images' / 'preview_rear.png').is_file()
    assert (package_dir / 'video' / 'preview.mp4').is_file()
    assert (package_dir / 'README.md').is_file()
    assert (package_dir / 'manifest.json').is_file()

    # 无未捕获异常；成本字段 ≥0
    skill_runs = db.list_skill_runs(run_id)
    assert skill_runs
    assert all((s.get('cost_cny') or 0) >= 0 for s in skill_runs)
    assert detail['total_cost_cny'] >= 0


async def test_e2e_images_failed_still_packages_pdf(artifact_root: Path):
    """剧本 D2：生图全失败 → F5 ready_with_warnings 仅 PDF。"""

    class FailImageClient:
        async def submit_t2i(self, **kwargs):
            from media.dashscope_image import ImageClientError

            raise ImageClientError('all fail', retryable=False)

        async def wait_task(self, task_id, *, timeout_sec=None):
            raise ImageClientError('no')

        async def download(self, url, dest):
            raise ImageClientError('no')

    user_id = db.create_user(f'e2e_d2_{id(object())}', 'hash', role='user')
    session_id = db.create_session(user_id, _form_state())
    run_id = db.create_pipeline_run(session_id=session_id, user_id=user_id)

    detail = await run_pipeline(
        run_id,
        form_state=_form_state(),
        llm_json=_mock_llm,
        search_fn=_mock_search,
        image_client=FailImageClient(),
        video_client=FakeVideoClient(),
        artifact_root=artifact_root,
    )

    assert detail['raw_status'] in {'ready', 'ready_with_warnings'}
    assert detail['skills']['images'] == 'failed'
    package_dir = artifact_root / run_id / 'package'
    assert (package_dir / 'docs' / 'plan.pdf').is_file() or (package_dir / 'docs' / 'plan.docx').is_file()
    assert not (package_dir / 'video' / 'preview.mp4').is_file()


async def test_e2e_plan_failed_no_package(artifact_root: Path):
    """剧本 M5 / B2：F2 失败 → F5 failed，不产出空包。"""

    async def bad_llm(system: str, user: str) -> dict:
        if '检索意图' in system or '检索策略' in system:
            return []
        raise RuntimeError('LLM 挂了')

    user_id = db.create_user(f'e2e_m5_{id(object())}', 'hash', role='user')
    session_id = db.create_session(user_id, _form_state())
    run_id = db.create_pipeline_run(session_id=session_id, user_id=user_id)

    # 无知识库命中 → degraded 模板方案，不是 failed。
    # 为测 M5，直接让 form 缺核心字段。
    empty_state = to_dict(create_initial_state())
    detail = await run_pipeline(
        run_id,
        form_state=empty_state,
        llm_json=_mock_llm,
        search_fn=_mock_search,
        image_client=FakeImageClient(),
        video_client=FakeVideoClient(),
        artifact_root=artifact_root,
    )
    assert detail['raw_status'] == 'failed'
    package_dir = artifact_root / run_id / 'package'
    assert not (package_dir / 'README.md').is_file()
    assert not list(package_dir.rglob('*')) if package_dir.exists() else True


async def test_e2e_idempotent_reuse_media(artifact_root: Path):
    """剧本 E：二次跑复用媒体，不双计费。"""
    user_id = db.create_user(f'e2e_idem_{id(object())}', 'hash', role='user')
    session_id = db.create_session(user_id, _form_state())
    run_id = db.create_pipeline_run(session_id=session_id, user_id=user_id)

    img_client = FakeImageClient()
    vid_client = FakeVideoClient()
    detail1 = await run_pipeline(
        run_id,
        form_state=_form_state(),
        llm_json=_mock_llm,
        search_fn=_mock_search,
        image_client=img_client,
        video_client=vid_client,
        artifact_root=artifact_root,
    )
    assert detail1['raw_status'] in {'ready', 'ready_with_warnings'}
    cost1 = detail1['total_cost_cny']
    img_submits = img_client.submits
    vid_submits = vid_client.submits

    # 同 run 再跑：plan/images/video 都应复用
    detail2 = await run_pipeline(
        run_id,
        form_state=_form_state(),
        llm_json=_mock_llm,
        search_fn=_mock_search,
        image_client=img_client,
        video_client=vid_client,
        artifact_root=artifact_root,
    )
    assert detail2['raw_status'] in {'ready', 'ready_with_warnings'}
    assert img_client.submits == img_submits
    assert vid_client.submits == vid_submits
    # 二次跑可能新增 final_package 成本，但媒体成本不增加
    assert detail2['total_cost_cny'] >= cost1 - 0.001
