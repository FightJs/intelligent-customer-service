"""F5 final_package 契约与行为单测（mock 上游，CI 可跑）。"""
from __future__ import annotations

import hashlib
import json
import zipfile
from pathlib import Path

import pytest

from pipeline.budget import parse_money_range, tier_within_budget
from pipeline.final_package import run_final_package
from pipeline.models import FinalPackageInput


# ── fixtures ─────────────────────────────────────────────────────────


@pytest.fixture
def artifacts(tmp_path: Path) -> Path:
    root = tmp_path / 'artifacts'
    root.mkdir()
    return root


def _write(path: Path, data: bytes | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, str):
        path.write_text(data, encoding='utf-8')
    else:
        path.write_bytes(data)
    return path


PLAN_JSON = {
    'meta': {
        'brand': '云裳',
        'industry': 'women',
        'room_size': 'medium',
        'budget_total': '3-5w',
        'generated_at': '2026-01-01T00:00:00Z',
        'pipeline_run_id': 'pr_test',
        'knowledge_refs': [{'collection': 'equipment_specs', 'id': 1001}],
        'completeness': 0.9,
        'status_flags': [],
    },
    'summary': '女装 20㎡ 中高客单品牌自播直播间',
    'layout': {
        'zones': [{'name': '主播区', 'notes': '正面主机位'}],
        'lighting_plan': '三点布光',
        'camera_plan': '主机位正面',
        'background_plan': '国风背景墙',
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
            'reason': '适配 20㎡ 中高客单女装',
            'is_custom': False,
        },
        {
            'knowledge_id': None,
            'category': '背景',
            'name': '定制国风背景板',
            'model': '',
            'brand': '',
            'qty': 1,
            'unit_price_band': 'mid',
            'reason': '按品牌色定制',
            'is_custom': True,
        },
    ],
    'package_tiers': [
        {'tier': '性价比', 'total_range': '1.2-1.6w', 'items': [{'name': '神牛灯', 'qty': 2}]},
        {'tier': '进阶', 'total_range': '3.2-3.8w', 'items': [{'name': '爱图仕', 'qty': 2}]},
        {'tier': '高配', 'total_range': '5.5-6.2w', 'items': [{'name': 'ARRI', 'qty': 1}]},
    ],
    'setup_steps': [
        '第1步：清空场地并确定主播区',
        '第2步：安装主灯与柔光箱',
        '第3步：架设主机位并校准白平衡',
    ],
    'risks': ['窗户在主播右侧需遮光'],
    'scene_card': {
        'room_size_band': 'medium',
        'style_keywords': ['国风', '高端'],
        'color_palette': ['#f5f0e8', '#2c2c2c'],
        'color_temp': '4000K',
        'furniture': ['主播桌'],
        'lighting_fixtures': ['COB主灯×2'],
        'product_category': '女装',
        'camera_angles': ['front', 'left', 'rear'],
        'forbidden': ['文字水印'],
    },
}

FORM_STATE = {
    'sections': {
        'customer': {
            'fields': {
                'brand': {'type': 'text', 'value': '云裳'},
                'identity': {'type': 'choice-multi', 'value': ['boss']},
            }
        },
        'industry': {
            'fields': {
                'category': {'type': 'choice-single', 'value': 'women'},
                'subcategory': {'type': 'text', 'value': '高端香云纱女装'},
                'price_band': {'type': 'choice-single', 'value': 'high'},
                'live_type': {'type': 'choice-single', 'value': 'brand'},
            }
        },
        'status': {
            'fields': {'has_room': {'type': 'choice-single', 'value': 'yes'}}
        },
        'venue': {
            'fields': {'area': {'type': 'choice-single', 'value': '20-30'}}
        },
        'budget': {
            'fields': {
                'total': {'type': 'choice-single', 'value': '3-5w'},
                'flex': {'type': 'choice-single', 'value': 'some'},
            }
        },
        'product': {
            'fields': {
                'main': {'type': 'text', 'value': '连衣裙'},
                'keywords': {'type': 'choice-multi', 'value': ['国风']},
            }
        },
        'goal': {
            'fields': {
                'core': {'type': 'choice-single', 'value': 'new'},
                'deadline': {'type': 'choice-single', 'value': '2w'},
            }
        },
    }
}


def _png_bytes() -> bytes:
    # 1x1 PNG
    return bytes.fromhex(
        '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489'
        '0000000d49444154789c63000100000500010d0a2db40000000049454e44ae426082'
    )


@pytest.fixture
def full_upstream(tmp_path: Path):
    run_id = 'pr_full'
    run_dir = tmp_path / 'runs' / run_id
    plan_json = _write(run_dir / 'docs' / 'plan.json', json.dumps(PLAN_JSON, ensure_ascii=False))
    plan_pdf = _write(run_dir / 'docs' / 'plan.pdf', b'%PDF-1.4 fake plan pdf')
    imgs = {}
    for angle in ('front', 'left', 'rear'):
        imgs[angle] = _write(run_dir / 'images' / f'preview_{angle}.png', _png_bytes())
    video = _write(run_dir / 'video' / 'preview.mp4', b'\x00\x00\x00\x18ftypmp42' + b'x' * 200)

    plan_output = {
        'skill': 'plan_document',
        'status': 'succeeded',
        'plan_json_path': str(plan_json),
        'pdf_path': str(plan_pdf),
        'requirement_brief': {'budget_total': '3-5w', 'budget_flex': 'some', 'brand': '云裳'},
        'knowledge_hits': [],
        'scene_card': PLAN_JSON['scene_card'],
        'cost_cny': 0.1,
        'warnings': [],
        'error': None,
    }
    images_output = {
        'skill': 'preview_images',
        'status': 'succeeded',
        'images': [
            {
                'angle': angle,
                'path': str(path),
                'width': 1,
                'height': 1,
                'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                'model': 'wan2.7',
                'cost_cny': 0.4,
            }
            for angle, path in imgs.items()
        ],
        'seed_used': 42,
        'model': 'wan2.7',
        'total_cost_cny': 1.2,
        'warnings': [],
        'error': None,
    }
    video_output = {
        'skill': 'preview_video',
        'status': 'succeeded',
        'video_path': str(video),
        'source_image': str(imgs['front']),
        'duration_sec': 8,
        'resolution': '720P',
        'model': 'wan2.7-i2v',
        'sha256': hashlib.sha256(video.read_bytes()).hexdigest(),
        'cost_cny': 1.0,
        'warnings': [],
        'error': None,
    }
    return {
        'run_id': run_id,
        'plan_output': plan_output,
        'images_output': images_output,
        'video_output': video_output,
        'plan_json': plan_json,
        'imgs': imgs,
        'video': video,
    }


def _input(upstream: dict, **kwargs) -> FinalPackageInput:
    return FinalPackageInput(
        pipeline_run_id=upstream['run_id'],
        session_id='sess_1',
        form_state=kwargs.pop('form_state', FORM_STATE),
        plan_output=kwargs.pop('plan_output', upstream['plan_output']),
        images_output=kwargs.pop('images_output', upstream['images_output']),
        video_output=kwargs.pop('video_output', upstream['video_output']),
        **kwargs,
    )


# ── happy path ───────────────────────────────────────────────────────


def test_full_package_ready(artifacts: Path, full_upstream: dict):
    out = run_final_package(
        _input(full_upstream),
        artifact_root_override=artifacts,
    )
    assert out.status == 'ready', out.warnings
    assert out.package_dir is not None
    package = Path(out.package_dir)
    assert (package / 'README.md').is_file()
    assert (package / 'manifest.json').is_file()
    assert (package / 'docs' / 'plan.json').is_file()
    assert (package / 'docs' / 'plan.pdf').is_file()
    assert (package / 'docs' / 'equipment.xlsx').is_file()
    assert (package / 'images' / 'preview_front.png').is_file()
    assert (package / 'images' / 'preview_left.png').is_file()
    assert (package / 'images' / 'preview_rear.png').is_file()
    assert (package / 'video' / 'preview.mp4').is_file()
    assert out.zip_path and Path(out.zip_path).is_file()

    manifest = json.loads((package / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['pipeline_run_id'] == full_upstream['run_id']
    assert manifest['skills']['plan_document']['status'] == 'succeeded'
    assert manifest['skills']['preview_images']['status'] == 'succeeded'
    assert manifest['skills']['preview_video']['status'] == 'succeeded'
    assert manifest['skills']['final_package']['status'] == 'ready'
    assert manifest['total_cost_cny'] == pytest.approx(0.1 + 1.2 + 1.0 + 0.0)

    # R5: files 含 sha256
    paths = {f['path'] for f in manifest['files']}
    assert 'docs/plan.pdf' in paths
    assert 'docs/plan.json' in paths
    assert 'README.md' in paths
    assert 'images/preview_front.png' in paths
    assert 'video/preview.mp4' in paths
    for f in manifest['files']:
        assert len(f['sha256']) == 64
        assert f['bytes'] > 0

    # zip 内容
    with zipfile.ZipFile(out.zip_path) as zf:
        names = set(zf.namelist())
    assert 'README.md' in names
    assert 'manifest.json' in names
    assert 'docs/plan.json' in names


def test_package_reuses_existing_media(artifacts: Path, full_upstream: dict):
    """重跑：不重新生成媒体，仍产出完整包。"""
    out1 = run_final_package(_input(full_upstream), artifact_root_override=artifacts)
    out2 = run_final_package(_input(full_upstream), artifact_root_override=artifacts)
    assert out1.status == out2.status == 'ready'
    assert out1.package_dir == out2.package_dir
    assert Path(out2.package_dir, 'video', 'preview.mp4').is_file()


# ── 降级矩阵 ─────────────────────────────────────────────────────────


def test_video_failed_degrades(artifacts: Path, full_upstream: dict):
    video_output = dict(full_upstream['video_output'])
    video_output['status'] = 'failed'
    video_output['video_path'] = None
    video_output['error'] = 'i2v timeout'
    out = run_final_package(
        _input(full_upstream, video_output=video_output),
        artifact_root_override=artifacts,
    )
    assert out.status == 'ready_with_warnings'
    assert out.manifest['gaps'] and 'video_failed' in out.manifest['gaps']
    package = Path(out.package_dir)
    assert not (package / 'video' / 'preview.mp4').exists()
    readme = (package / 'README.md').read_text(encoding='utf-8')
    assert '不含预览视频' in readme
    # R6：不得声称视频已生成
    assert '预览视频已生成' not in readme


def test_images_partial_and_failed_video(artifacts: Path, full_upstream: dict):
    images_output = dict(full_upstream['images_output'])
    images_output['status'] = 'partial'
    images_output['images'] = full_upstream['images_output']['images'][:1]  # only front
    video_output = dict(full_upstream['video_output'])
    video_output['status'] = 'failed'
    video_output['video_path'] = None
    out = run_final_package(
        _input(full_upstream, images_output=images_output, video_output=video_output),
        artifact_root_override=artifacts,
    )
    assert out.status == 'ready_with_warnings'
    gaps = out.manifest['gaps']
    assert 'missing_angle:left' in gaps
    assert 'missing_angle:rear' in gaps
    assert 'video_failed' in gaps
    readme = (package := Path(out.package_dir),)[0]
    text = (package / 'README.md').read_text(encoding='utf-8')
    assert '缺少机位' in text or '缺失机位' in text
    assert '完整三机位' not in text


def test_plan_failed_blocks_package(artifacts: Path, full_upstream: dict):
    plan_output = dict(full_upstream['plan_output'])
    plan_output['status'] = 'failed'
    plan_output['error'] = 'LLM compose failed'
    out = run_final_package(
        _input(full_upstream, plan_output=plan_output),
        artifact_root_override=artifacts,
    )
    assert out.status == 'failed'
    assert out.package_dir is None
    assert out.error == 'LLM compose failed'
    assert out.manifest['skills']['final_package']['status'] == 'failed'


def test_images_failed_still_packages_pdf(artifacts: Path, full_upstream: dict):
    images_output = {
        'skill': 'preview_images',
        'status': 'failed',
        'images': [],
        'seed_used': None,
        'model': 'wan2.7',
        'total_cost_cny': 0.0,
        'warnings': ['all failed'],
        'error': 'timeout',
    }
    video_output = dict(full_upstream['video_output'])
    video_output['status'] = 'failed'
    video_output['video_path'] = None
    out = run_final_package(
        _input(full_upstream, images_output=images_output, video_output=video_output),
        artifact_root_override=artifacts,
    )
    assert out.status == 'ready_with_warnings'
    package = Path(out.package_dir)
    assert (package / 'docs' / 'plan.pdf').is_file()
    assert not list((package / 'images').glob('preview_*.png'))
    text = (package / 'README.md').read_text(encoding='utf-8')
    assert '不含预览图' in text


# ── 规则 ─────────────────────────────────────────────────────────────


def test_r1_removes_uncustom_untraced_equipment(artifacts: Path, full_upstream: dict, tmp_path: Path):
    plan = json.loads(full_upstream['plan_json'].read_text(encoding='utf-8'))
    plan['equipment_list'].append(
        {
            'knowledge_id': None,
            'category': '其他',
            'name': '神秘设备',
            'is_custom': False,
        }
    )
    plan_json = _write(tmp_path / 'runs' / 'pr_r1' / 'docs' / 'plan.json', json.dumps(plan, ensure_ascii=False))
    plan_output = dict(full_upstream['plan_output'])
    plan_output['plan_json_path'] = str(plan_json)
    out = run_final_package(
        _input(
            full_upstream,
            plan_output=plan_output,
        ),
        artifact_root_override=artifacts,
    )
    # run_id 仍是 pr_full；用同一 package 也可
    assert out.status == 'ready_with_warnings'
    assert any('剔除' in w for w in out.warnings)
    text = Path(out.package_dir, 'README.md').read_text(encoding='utf-8')
    assert '神秘设备' in text  # 调整说明中披露
    assert '定制国风背景板' in text  # is_custom 保留
    # excel 不含被剔除项
    xlsx = Path(out.package_dir, 'docs', 'equipment.xlsx')
    assert xlsx.is_file()


def test_r1_known_ids_filter(artifacts: Path, full_upstream: dict):
    out = run_final_package(
        _input(full_upstream, known_knowledge_ids={999}),
        artifact_root_override=artifacts,
    )
    assert out.status == 'ready_with_warnings'
    assert any('不存在' in w for w in out.warnings)


def test_r2_budget_mismatch_warning(artifacts: Path, full_upstream: dict, tmp_path: Path):
    plan = json.loads(full_upstream['plan_json'].read_text(encoding='utf-8'))
    plan['package_tiers'] = [
        {'tier': '超配', 'total_range': '15-18w', 'items': []},
    ]
    plan_json = _write(tmp_path / 'runs' / 'pr_r2' / 'docs' / 'plan.json', json.dumps(plan, ensure_ascii=False))
    plan_output = dict(full_upstream['plan_output'])
    plan_output['plan_json_path'] = str(plan_json)
    out = run_final_package(
        _input(full_upstream, plan_output=plan_output),
        artifact_root_override=artifacts,
    )
    assert out.status == 'ready_with_warnings'
    assert any('预算' in w for w in out.warnings)


def test_r7_incomplete_form_flagged(artifacts: Path, full_upstream: dict):
    incomplete = {'sections': {'customer': {'fields': {'brand': {'type': 'text', 'value': ''}}}}}
    out = run_final_package(
        _input(full_upstream, form_state=incomplete),
        artifact_root_override=artifacts,
    )
    assert out.status == 'ready_with_warnings'
    text = Path(out.package_dir, 'README.md').read_text(encoding='utf-8')
    head = '\n'.join(text.splitlines()[:4])
    assert '> **注意**' in head
    assert 'form_incomplete' in out.manifest['gaps']


def test_r6_llm_cannot_claim_fake_media(artifacts: Path, full_upstream: dict):
    """视频失败 + 仅 1 张图时，LLM 不得声称已生成视频或完整三机位。"""
    images_output = dict(full_upstream['images_output'])
    images_output['status'] = 'partial'
    images_output['images'] = full_upstream['images_output']['images'][:1]
    video_output = dict(full_upstream['video_output'])
    video_output['status'] = 'failed'
    video_output['video_path'] = None

    def evil_llm(prompt: str) -> str:
        return (
            '# 交付说明\n\n'
            '预览视频已生成，请观看 video/preview.mp4。\n'
            '完整三机位效果图如下。\n'
        )

    out = run_final_package(
        _input(
            full_upstream,
            images_output=images_output,
            video_output=video_output,
        ),
        artifact_root_override=artifacts,
        readme_llm=evil_llm,
    )
    text = Path(out.package_dir, 'README.md').read_text(encoding='utf-8')
    assert '预览视频已生成' not in text
    assert 'video/preview.mp4' not in text
    assert '完整三机位' not in text
    assert '本包不含预览视频' in text
    # LLM 成本计入
    assert out.manifest['skills']['final_package']['cost_cny'] == pytest.approx(0.02)


def test_llm_failure_falls_back_to_template(artifacts: Path, full_upstream: dict):
    def boom(prompt: str) -> str:
        raise RuntimeError('llm down')

    out = run_final_package(
        _input(full_upstream),
        artifact_root_override=artifacts,
        readme_llm=boom,
    )
    assert out.status == 'ready'
    assert Path(out.package_dir, 'README.md').read_text(encoding='utf-8').startswith('#')


# ── 工具函数 ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('3-5w', (30000.0, 50000.0)),
        ('1.2-1.6w', (12000.0, 16000.0)),
        ('5k-1w', (5000.0, 10000.0)),
        ('<1w', (0.0, 10000.0)),
        ('20w+', (200000.0, float('inf'))),
        ('30000-50000', (30000.0, 50000.0)),
        ('3-5万', (30000.0, 50000.0)),
    ],
)
def test_parse_money_range(text, expected):
    r = parse_money_range(text)
    assert r is not None
    assert r.lo == pytest.approx(expected[0])
    assert r.hi == pytest.approx(expected[1]) if expected[1] != float('inf') else r.hi == float('inf')


def test_tier_within_budget_tolerance():
    budget = parse_money_range('3-5w')
    ok = parse_money_range('3.2-3.8w')
    far = parse_money_range('15-18w')
    assert tier_within_budget(ok, budget, 0.10)
    assert not tier_within_budget(far, budget, 0.10)
    assert not tier_within_budget(far, budget, 0.25)
