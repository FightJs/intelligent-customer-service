"""F3 preview_images skill 单测。Mock 生图客户端，不依赖外网。"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from media.dashscope_image import ImageClientError, PNG_MAGIC
from pipeline.models import PreviewImagesInput
from pipeline.skills.preview_images import (
    ANGLE_ORDER,
    build_angle_prompt,
    build_common_lock,
    resolve_angles,
    run_preview_images,
)
from pipeline.models import SceneCard


class FakeImageClient:
    """按 fail_angles / fail_all 控制成败的假客户端。"""

    def __init__(
        self,
        *,
        fail_angles: set[str] | None = None,
        fail_models: set[str] | None = None,
        fail_all: bool = False,
        corrupt_first_n: int = 0,
        image_bytes: int = 2048,
    ):
        self.fail_angles = fail_angles or set()
        self.fail_models = fail_models or set()
        self.fail_all = fail_all
        self.corrupt_first_n = corrupt_first_n
        self.image_bytes = image_bytes
        self.submits: list[dict] = []
        self.downloads = 0
        self._task_seq = 0

    async def submit_t2i(self, *, model, prompt, seed=None, size='1280*720', n=1) -> str:
        self.submits.append({'model': model, 'prompt': prompt, 'seed': seed, 'size': size, 'n': n})
        if self.fail_all or model in self.fail_models:
            raise ImageClientError(f'model {model} unavailable')
        for angle in ANGLE_ORDER:
            # prompt 里有机位描述
            if angle == 'front' and 'front view' in prompt:
                if angle in self.fail_angles:
                    raise ImageClientError(f'{angle} failed')
            if angle == 'left' and 'left side' in prompt:
                if angle in self.fail_angles:
                    raise ImageClientError(f'{angle} failed')
            if angle == 'rear' and 'rear-right' in prompt:
                if angle in self.fail_angles:
                    raise ImageClientError(f'{angle} failed')
        self._task_seq += 1
        return f'img-task-{self._task_seq}'

    async def wait_task(self, task_id: str, *, timeout_sec=None):
        class _R:
            status = 'SUCCEEDED'
            image_urls = ['https://example.com/img.png']
            seed = 42
            message = None

        return _R()

    async def download(self, url: str, dest: Path) -> Path:
        self.downloads += 1
        dest.parent.mkdir(parents=True, exist_ok=True)
        if self.downloads <= self.corrupt_first_n:
            dest.write_bytes(b'')
        else:
            dest.write_bytes(PNG_MAGIC + b'0' * self.image_bytes)
        return dest


@pytest.fixture
def artifacts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / 'artifacts'
    monkeypatch.setenv('ARTIFACT_ROOT', str(root))
    monkeypatch.setenv('IMAGE_MODEL', 'wan2.7-image')
    monkeypatch.setenv('IMAGE_FALLBACK_MODEL', 'qwen-image')
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


def test_build_prompt_contains_common_lock_and_angle():
    card = SceneCard(
        style_keywords=['国风'],
        color_palette=['#ffffff'],
        product_category='女装',
        forbidden=['文字水印'],
    )
    lock = build_common_lock(card)
    assert 'same room' in lock
    assert '女装' in lock
    prompt = build_angle_prompt(card, 'front')
    assert 'front view' in prompt
    assert 'no 文字水印' in prompt


def test_resolve_angles_defaults_and_truncates():
    card = SceneCard()
    assert resolve_angles(card, 3) == list(ANGLE_ORDER)
    assert resolve_angles(card, 1) == ['front']


async def test_success_three_images(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    client = FakeImageClient()
    out = await run_preview_images(
        PreviewImagesInput(
            pipeline_run_id='pr_img_ok',
            plan_json_path=str(plan),
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert len(out.images) == 3
    assert {img.angle for img in out.images} == set(ANGLE_ORDER)
    for img in out.images:
        assert Path(img.path).is_file()
        assert Path(img.path).stat().st_size > 100
        assert img.sha256
        assert img.seed == 42
    assert out.seed_used == 42
    assert out.total_cost_cny > 0
    manifest = artifacts_root / 'pr_img_ok' / 'images' / 'manifest.json'
    assert manifest.is_file()
    from store import db

    skill_runs = [
        r for r in db.list_skill_runs('pr_img_ok') if r['skill'] == 'preview_images'
    ]
    assert skill_runs
    assert skill_runs[-1]['status'] == 'succeeded'


async def test_partial_two_images(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    client = FakeImageClient(fail_angles={'rear'})
    out = await run_preview_images(
        PreviewImagesInput(
            pipeline_run_id='pr_img_partial',
            plan_json_path=str(plan),
            allow_partial=True,
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'partial'
    assert len(out.images) == 2
    assert out.error is None
    assert any('缺失机位' in w for w in out.warnings)


async def test_all_fail(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    client = FakeImageClient(fail_all=True)
    out = await run_preview_images(
        PreviewImagesInput(
            pipeline_run_id='pr_img_fail',
            plan_json_path=str(plan),
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'failed'
    assert out.images == []
    # 无空文件残留
    img_dir = artifacts_root / 'pr_img_fail' / 'images'
    if img_dir.is_dir():
        for p in img_dir.glob('preview_*.png'):
            assert p.stat().st_size > 0


async def test_corrupt_image_retried(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    client = FakeImageClient(corrupt_first_n=1)
    out = await run_preview_images(
        PreviewImagesInput(
            pipeline_run_id='pr_img_corrupt',
            plan_json_path=str(plan),
        ),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert len(out.images) == 3


async def test_idempotent_reuse(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    client = FakeImageClient()
    out1 = await run_preview_images(
        PreviewImagesInput(pipeline_run_id='pr_img_reuse', plan_json_path=str(plan)),
        client=client,
        root=artifacts_root,
    )
    assert out1.status == 'succeeded'
    submits_before = len(client.submits)

    out2 = await run_preview_images(
        PreviewImagesInput(pipeline_run_id='pr_img_reuse', plan_json_path=str(plan)),
        client=client,
        root=artifacts_root,
    )
    assert out2.status == 'succeeded'
    assert out2.total_cost_cny == 0.0
    assert any('复用' in w for w in out2.warnings)
    assert len(client.submits) == submits_before


async def test_force_regenerates(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    client = FakeImageClient()
    await run_preview_images(
        PreviewImagesInput(pipeline_run_id='pr_img_force', plan_json_path=str(plan)),
        client=client,
        root=artifacts_root,
    )
    submits_before = len(client.submits)
    out = await run_preview_images(
        PreviewImagesInput(pipeline_run_id='pr_img_force', plan_json_path=str(plan), force=True),
        client=client,
        root=artifacts_root,
    )
    assert out.status == 'succeeded'
    assert len(client.submits) > submits_before


async def test_partial_retry_only_missing(artifacts_root: Path, tmp_path: Path):
    plan = _make_plan(tmp_path / 'plan.json')
    client = FakeImageClient(fail_angles={'rear'})
    out1 = await run_preview_images(
        PreviewImagesInput(
            pipeline_run_id='pr_img_fill',
            plan_json_path=str(plan),
            allow_partial=True,
        ),
        client=client,
        root=artifacts_root,
    )
    assert out1.status == 'partial'

    # 修好 rear 后重试（不 force）：只补缺失机位
    client2 = FakeImageClient()
    out2 = await run_preview_images(
        PreviewImagesInput(
            pipeline_run_id='pr_img_fill',
            plan_json_path=str(plan),
            allow_partial=True,
        ),
        client=client2,
        root=artifacts_root,
    )
    assert out2.status == 'succeeded'
    assert len(out2.images) == 3
    # 仅补 rear 一张
    assert len(client2.submits) == 1
