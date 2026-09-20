"""F4 preview_video skill 单测。Mock DashScope，不依赖外网。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from media.dashscope_video import VideoClientError
from pipeline import store
from pipeline.models import PreviewVideoInput
from pipeline.skills import preview_video as pv
from pipeline.skills.preview_video import (
    build_motion_prompt,
    estimate_cost,
    run_preview_video,
    select_source_image,
)
from pipeline.models import SceneCard

MIN_BYTES = pv.MIN_VIDEO_BYTES


class FakeVideoClient:
    """内存假客户端：按 model/resolution 控制成败。"""

    def __init__(
        self,
        *,
        fail_models: set[str] | None = None,
        fail_resolutions: set[str] | None = None,
        fail_download_times: int = 0,
        video_size: int = MIN_BYTES + 1024,
        timeout_on_wait: bool = False,
    ):
        self.fail_models = fail_models or set()
        self.fail_resolutions = fail_resolutions or set()
        self.fail_download_times = fail_download_times
        self.video_size = video_size
        self.timeout_on_wait = timeout_on_wait
        self.submits: list[dict] = []
        self.downloads = 0
        self._task_seq = 0

    async def submit_i2v(self, *, model, prompt, image_path, duration_sec, resolution) -> str:
        self.submits.append(
            {
                'model': model,
                'prompt': prompt,
                'image_path': Path(image_path),
                'duration_sec': duration_sec,
                'resolution': resolution,
            }
        )
        if model in self.fail_models:
            raise VideoClientError(f'model {model} unavailable')
        if resolution in self.fail_resolutions:
            raise VideoClientError(f'resolution {resolution} unavailable')
        self._task_seq += 1
        return f'task-{self._task_seq}'

    async def wait_task(self, task_id: str, *, timeout_sec=None):
        if self.timeout_on_wait:
            raise VideoClientError(f'视频任务超时: {task_id}')

        class _R:
            status = 'SUCCEEDED'
            video_url = 'https://example.com/preview.mp4'
            message = None

        return _R()

    async def download(self, url: str, dest: Path) -> Path:
        self.downloads += 1
        if self.downloads <= self.fail_download_times:
            dest.write_bytes(b'')  # 0 字节损坏
            return dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'0' * self.video_size)
        return dest


@pytest.fixture
def artifacts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / 'artifacts'
    monkeypatch.setenv('ARTIFACT_ROOT', str(root))
    monkeypatch.delenv('VIDEO_TIER', raising=False)
    monkeypatch.setenv('VIDEO_MODEL', 'wan2.7-i2v')
    monkeypatch.setenv('VIDEO_FALLBACK_MODEL', 'kling-v3-video')
    return root


def _make_plan(path: Path, scene_card: dict | None = None) -> Path:
    payload = {
        'meta': {'brand': '云裳'},
        'scene_card': scene_card
        or {
            'room_size_band': 'medium',
            'style_keywords': ['国风', '高端'],
            'color_palette': ['#f5f0e8', '#2c2c2c'],
            'color_temp': '4000K',
            'furniture': ['主播桌'],
            'lighting_fixtures': ['COB主灯'],
            'product_category': '女装',
            'camera_angles': ['front', 'left', 'rear'],
            'forbidden': ['文字水印', '品牌logo'],
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding='utf-8')
    return path


def _make_image(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b'\x89PNG\r\n\x1a\n' + b'0' * 2000)
    return path


def _images(base: Path, *angles: str) -> list[dict]:
    items = []
    for angle in angles:
        p = _make_image(base / f'preview_{angle}.png')
        items.append({'angle': angle, 'path': str(p), 'seed': 1})
    return items


async def test_no_images_fails(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-noimg',
            plan_json_path=str(plan),
            images=[],
        ),
        client=FakeVideoClient(),
        root=artifacts_root,
    )
    assert out.status == 'failed'
    assert '无可用' in (out.error or '')
    assert out.video_path is None
    assert not list(artifacts_root.rglob('*.mp4'))


async def test_invalid_duration_fails(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-dur',
            plan_json_path=str(plan),
            images=images,
            duration_sec=3,
        ),
        client=FakeVideoClient(),
        root=artifacts_root,
    )
    assert out.status == 'failed'
    assert 'duration_sec' in (out.error or '')


async def test_success_front_writes_mp4_and_meta(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front', 'left', 'rear')
    client = FakeVideoClient()
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-ok',
            plan_json_path=str(plan),
            images=images,
            duration_sec=8,
            resolution='720P',
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert out.video_path and Path(out.video_path).is_file()
    assert Path(out.video_path).stat().st_size >= MIN_BYTES
    assert out.source_image and 'preview_front' in out.source_image
    assert out.resolution == '720P'
    assert out.model == 'wan2.7-i2v'
    assert out.sha256
    assert out.cost_cny > 0

    meta_path = artifacts_root / 'run-ok' / 'video' / 'meta.json'
    assert meta_path.is_file()
    meta = json.loads(meta_path.read_text(encoding='utf-8'))
    assert meta['source_angle'] == 'front'
    assert meta['duration_sec'] == 8

    prompt = client.submits[0]['prompt']
    assert '国风' in prompt
    assert '4000K' in prompt
    assert '不要出现文字水印' in prompt
    assert '主播桌' in prompt
    assert 'COB主灯' in prompt
    assert '以给定首帧图为唯一起点' in prompt
    assert '正机位' in prompt

    art = store.find_latest_video_artifact('run-ok')
    assert art and art['path'] == out.video_path


async def test_fallback_angle_when_front_missing(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'left', 'rear')
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-left',
            plan_json_path=str(plan),
            images=images,
            source_angle='front',
        ),
        client=FakeVideoClient(),
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert out.source_image and 'preview_left' in out.source_image
    assert any('顺延' in w for w in out.warnings)


async def test_1080p_falls_back_to_720p(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    client = FakeVideoClient(fail_resolutions={'1080P'})
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-1080',
            plan_json_path=str(plan),
            images=images,
            resolution='1080P',
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert out.resolution == '720P'
    assert any('降级' in w for w in out.warnings)
    assert {s['resolution'] for s in client.submits} == {'1080P', '720P'}


async def test_primary_model_falls_back_to_backup(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    client = FakeVideoClient(fail_models={'wan2.7-i2v'})
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-model',
            plan_json_path=str(plan),
            images=images,
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert out.model == 'kling-v3-video'
    assert client.submits[0]['model'] == 'wan2.7-i2v'
    assert client.submits[-1]['model'] == 'kling-v3-video'


async def test_timeout_fails(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-timeout',
            plan_json_path=str(plan),
            images=images,
        ),
        client=FakeVideoClient(timeout_on_wait=True),
        root=artifacts_root,
    )
    assert out.status == 'failed'
    assert '超时' in (out.error or '') or '失败' in (out.error or '')


async def test_zero_byte_retries_once_then_succeeds(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    client = FakeVideoClient(fail_download_times=1)
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-corrupt',
            plan_json_path=str(plan),
            images=images,
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert client.downloads >= 2


async def test_idempotent_reuse_existing_video(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    client = FakeVideoClient()
    first = await run_preview_video(
        PreviewVideoInput(pipeline_run_id='run-idem', plan_json_path=str(plan), images=images),
        client=client,
        root=artifacts_root,
    )
    assert first.status == 'succeeded'
    submits_after_first = len(client.submits)

    second = await run_preview_video(
        PreviewVideoInput(pipeline_run_id='run-idem', plan_json_path=str(plan), images=images),
        client=client,
        root=artifacts_root,
    )
    assert second.status == 'succeeded'
    assert second.reused is True
    assert second.video_path == first.video_path
    assert len(client.submits) == submits_after_first


async def test_force_regenerates(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    client = FakeVideoClient()
    await run_preview_video(
        PreviewVideoInput(pipeline_run_id='run-force', plan_json_path=str(plan), images=images),
        client=client,
        root=artifacts_root,
    )
    n = len(client.submits)
    out = await run_preview_video(
        PreviewVideoInput(
            pipeline_run_id='run-force',
            plan_json_path=str(plan),
            images=images,
            force=True,
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert out.reused is False
    assert len(client.submits) > n


async def test_flash_tier_uses_flash_model(artifacts_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv('VIDEO_TIER', 'flash')
    monkeypatch.setenv('VIDEO_FLASH_MODEL', 'wan2.6-i2v-flash')
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    client = FakeVideoClient()
    out = await run_preview_video(
        PreviewVideoInput(pipeline_run_id='run-flash', plan_json_path=str(plan), images=images),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert out.model == 'wan2.6-i2v-flash'
    assert client.submits[0]['model'] == 'wan2.6-i2v-flash'


async def test_all_attempts_fail_no_empty_mp4(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    images = _images(tmp_path / 'img', 'front')
    client = FakeVideoClient(fail_models={'wan2.7-i2v', 'kling-v3-video'})
    out = await run_preview_video(
        PreviewVideoInput(pipeline_run_id='run-allfail', plan_json_path=str(plan), images=images),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'failed'
    dest = artifacts_root / 'run-allfail' / 'video' / 'preview.mp4'
    assert not dest.exists() or dest.stat().st_size == 0
    # 成功校验不应写入 video artifact
    assert store.find_latest_video_artifact('run-allfail') is None


def test_select_source_image_priority():
    images = [
        {'angle': 'rear', 'path': '/r.png'},
        {'angle': 'left', 'path': '/l.png'},
    ]
    chosen, warnings = select_source_image(images, 'front')
    assert chosen and chosen['angle'] == 'left'
    assert warnings

    chosen2, _ = select_source_image([{'angle': 'front', 'path': '/f.png'}], 'front')
    assert chosen2 and chosen2['angle'] == 'front'

    none, _ = select_source_image([], 'front')
    assert none is None


def test_build_motion_prompt_from_scene_card():
    card = SceneCard(
        style_keywords=['极简'],
        color_palette=['#f5f0e8'],
        color_temp='5000K',
        furniture=['主播桌', '展示架'],
        lighting_fixtures=['COB主灯', '柔光箱'],
        product_category='美妆',
        room_size_band='small',
        forbidden=['品牌logo'],
    )
    prompt = build_motion_prompt(card, duration_sec=8, resolution='720P', source_angle='left')
    assert '极简' in prompt
    assert '#f5f0e8' in prompt
    assert '5000K' in prompt
    assert '美妆' in prompt
    assert '主播桌' in prompt
    assert 'COB主灯' in prompt
    assert 'small' in prompt
    assert '不要出现品牌logo' in prompt
    assert '时长约 8 秒' in prompt
    assert '以给定首帧图为唯一起点' in prompt
    assert '左侧机位' in prompt


def test_build_motion_prompt_front_and_rear_camera_moves():
    card = SceneCard(product_category='数码')
    front = build_motion_prompt(card, duration_sec=5, resolution='720P', source_angle='front')
    rear = build_motion_prompt(card, duration_sec=5, resolution='720P', source_angle='rear')
    assert '正机位' in front
    assert '纵深推进' in rear


def test_estimate_cost_tiers():
    assert estimate_cost(5, '720P', 'flash') < estimate_cost(5, '720P', 'standard')
    assert estimate_cost(5, '1080P', 'standard') > estimate_cost(5, '720P', 'standard')
