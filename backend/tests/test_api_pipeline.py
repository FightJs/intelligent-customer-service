"""Pipeline HTTP 契约与编排状态机测试。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import store.db as db
from agent.auth import create_token, hash_password
from api.app import app
from knowledge.models import KnowledgeHit
from media.dashscope_image import PNG_MAGIC
from pipeline.orchestrator import (
    build_pipeline_detail,
    run_pipeline,
    run_pipeline_from_skill,
)
from survey.state import create_initial_state, to_dict


@pytest.fixture
def artifact_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / 'artifacts'
    monkeypatch.setenv('ARTIFACT_ROOT', str(root))
    return root


@pytest.fixture
def client():
    return TestClient(app)


def _make_user(role: str = 'user') -> dict:
    username = f'u_{role}_{id(object())}_{db._now().replace(":", "").replace("+", "").replace(".", "")}'
    uid = db.create_user(username, hash_password('pass1234'), role=role)
    token = create_token({'id': uid, 'username': username, 'role': role})
    return {'id': uid, 'username': username, 'role': role, 'token': token}


def _auth(user: dict) -> dict[str, str]:
    return {'Authorization': f'Bearer {user["token"]}'}


def _form_state() -> dict:
    state = create_initial_state()
    state.sections['customer'].fields['brand'].value = '云裳'
    state.sections['industry'].fields['category'].value = 'women'
    state.sections['venue'].fields['area'].value = '20-30'
    state.sections['budget'].fields['total'].value = '3-5w'
    state.sections['budget'].fields['equipment'].value = '1-2w'
    state.sections['product'].fields['main'].value = '连衣裙'
    state.sections['product'].fields['keywords'].value = '国风'
    state.sections['goal'].fields['core'].value = 'new'
    return to_dict(state)


def test_guest_cannot_start_pipeline(client: TestClient):
    guest = _make_user('guest')
    # guest 登录由 guest_login 产生；直接用 role=guest token 也应 403
    resp = client.post(
        '/api/pipeline',
        headers=_auth(guest),
        json={'session_id': 's_missing'},
    )
    assert resp.status_code == 403


def test_owner_required_for_get(client: TestClient):
    owner = _make_user('user')
    other = _make_user('user')
    run_id = db.create_pipeline_run(session_id='s_x', user_id=owner['id'])

    resp = client.get(f'/api/pipeline/{run_id}', headers=_auth(other))
    assert resp.status_code == 403

    resp = client.get(f'/api/pipeline/{run_id}', headers=_auth(owner))
    assert resp.status_code == 200
    body = resp.json()
    assert body['id'] == run_id
    assert 'skills' in body
    assert set(body['skills'].keys()) == {'plan', 'images', 'video', 'package'}


def test_cancel_only_pending_running(client: TestClient):
    user = _make_user('user')
    run_id = db.create_pipeline_run(session_id='s_c', user_id=user['id'], status='pending')
    resp = client.post(f'/api/pipeline/{run_id}/cancel', headers=_auth(user))
    assert resp.status_code == 200
    assert db.get_pipeline_run(run_id)['status'] == 'cancelled'

    resp = client.post(f'/api/pipeline/{run_id}/cancel', headers=_auth(user))
    assert resp.status_code == 409


def test_concurrent_limit(client: TestClient, artifact_root: Path):
    user = _make_user('user')
    session_id = db.create_session(user['id'], _form_state())
    db.create_pipeline_run(session_id=session_id, user_id=user['id'], status='running')
    session = db.get_session(session_id)
    # 直接测 DB 层并发限制
    assert db.count_active_pipeline_runs(user['id']) == 1


def test_artifact_path_traversal_blocked(client: TestClient, artifact_root: Path):
    user = _make_user('user')
    run_id = db.create_pipeline_run(session_id='s_a', user_id=user['id'])
    # kind 必须是纯字母数字下划线
    for bad in ['a.b', 'x-y']:
        resp = client.get(
            f'/api/pipeline/{run_id}/artifacts/{bad}',
            headers=_auth(user),
        )
        assert resp.status_code == 400, (bad, resp.status_code, resp.text[:80])


async def test_retry_from_failed_images(artifact_root: Path):
    """ORCH-02：仅重试 failed skill，plan 不重跑。"""
    user_id = db.create_user(f'retry_{id(object())}', 'hash', role='user')
    session_id = db.create_session(user_id, _form_state())
    run_id = db.create_pipeline_run(session_id=session_id, user_id=user_id)

    async def _llm(system: str, user: str) -> dict:
        if '检索意图' in system or '检索策略' in system:
            return [{'collection': 'equipment_specs', 'query': '灯', 'filters': {}}]
        return {
            'summary': '测试方案',
            'layout': {
                'zones': [{'name': '主播区', 'notes': ''}],
                'lighting_plan': '三点布光',
                'camera_plan': '正面',
                'background_plan': '简洁背景',
            },
            'equipment_list': [
                {
                    'knowledge_id': 1001,
                    'category': '灯光',
                    'name': 'COB灯',
                    'model': 'X1',
                    'brand': 'B',
                    'qty': 1,
                    'unit_price_band': 'mid',
                    'reason': '主光',
                    'is_custom': False,
                }
            ],
            'package_tiers': [
                {'tier': '进阶', 'total_range': '3-4w', 'items': [{'name': 'COB', 'qty': 1}]},
            ],
            'setup_steps': [
                '步骤1准备场地材料与工具并确认尺寸。',
                '步骤2安装支架与灯光并固定点位。',
                '步骤3调试相机链路并试播验收。',
            ],
            'risks': [],
            'scene_card': {
                'room_size_band': 'medium',
                'style_keywords': ['现代'],
                'color_palette': ['#ffffff'],
                'color_temp': '4000K',
                'furniture': ['桌'],
                'lighting_fixtures': ['COB'],
                'product_category': '女装',
                'camera_angles': ['front', 'left', 'rear'],
                'forbidden': [],
            },
        }

    async def _search(intent):
        return [
            KnowledgeHit(
                collection='equipment_specs',
                id=1001,
                score=0.8,
                payload={'name': 'COB灯', 'text': '三点布光', 'industry': 'women'},
            )
        ]

    class FailImage:
        async def submit_t2i(self, **kwargs):
            from media.dashscope_image import ImageClientError

            raise ImageClientError('fail')

        async def wait_task(self, task_id, *, timeout_sec=None):
            raise ImageClientError('fail')

        async def download(self, url, dest):
            raise ImageClientError('fail')

    class OkImage:
        def __init__(self):
            self.n = 0

        async def submit_t2i(self, **kwargs):
            self.n += 1
            return f't{self.n}'

        async def wait_task(self, task_id, *, timeout_sec=None):
            class _R:
                status = 'SUCCEEDED'
                image_urls = ['https://e.com/x.png']
                seed = 1
                message = None

            return _R()

        async def download(self, url, dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(PNG_MAGIC + b'0' * 2000)
            return dest

    class OkVideo:
        async def submit_i2v(self, **kwargs):
            return 'v1'

        async def wait_task(self, task_id, *, timeout_sec=None):
            class _R:
                status = 'SUCCEEDED'
                video_url = 'https://e.com/v.mp4'
                message = None

            return _R()

        async def download(self, url, dest):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(b'0' * 120_000)
            return dest

    detail1 = await run_pipeline(
        run_id,
        form_state=_form_state(),
        llm_json=_llm,
        search_fn=_search,
        image_client=FailImage(),
        video_client=OkVideo(),
        artifact_root=artifact_root,
    )
    assert detail1['skills']['plan'] == 'succeeded'
    assert detail1['skills']['images'] == 'failed'
    assert detail1['raw_status'] in {'ready', 'ready_with_warnings', 'failed'}
    # 详情应携带完整方案内容，供前端方案清单渲染
    assert detail1.get('plan')
    assert detail1['plan'].get('equipment_list')
    assert detail1['plan'].get('layout')

    plan_path = artifact_root / run_id / 'docs' / 'plan.json'
    assert plan_path.is_file()
    plan_mtime = plan_path.stat().st_mtime_ns

    detail2 = await run_pipeline_from_skill(
        run_id,
        'preview_images',
        form_state=_form_state(),
        llm_json=_llm,
        search_fn=_search,
        image_client=OkImage(),
        video_client=OkVideo(),
        artifact_root=artifact_root,
    )
    assert detail2['skills']['images'] == 'succeeded'
    assert detail2['skills']['package'] == 'succeeded'
    # plan.json 未被重写
    assert plan_path.stat().st_mtime_ns == plan_mtime


def test_package_download_requires_ready(client: TestClient, artifact_root: Path):
    user = _make_user('user')
    run_id = db.create_pipeline_run(session_id='s_p', user_id=user['id'], status='running')
    resp = client.get(f'/api/pipeline/{run_id}/package', headers=_auth(user))
    assert resp.status_code == 409
