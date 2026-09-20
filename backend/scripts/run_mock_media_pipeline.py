"""Mock 媒体完整包试跑（OpenRouter 无余额时验证 F5 包结构）。"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
os.environ['MEDIA_PROVIDER'] = 'dashscope'  # 强制走本地 Fake 注入，不真实出图

from dotenv import load_dotenv

load_dotenv(BACKEND / '.env', override=True)

from store import db  # noqa: E402
from survey.state import create_initial_state, to_dict  # noqa: E402
from pipeline.orchestrator import run_pipeline  # noqa: E402
from media.dashscope_image import PNG_MAGIC  # noqa: E402


class FakeImageClient:
    def __init__(self):
        self.n = 0

    async def submit_t2i(self, *, model, prompt, seed=None, size='1280*720', n=1):
        self.n += 1
        return f't{self.n}'

    async def wait_task(self, task_id, *, timeout_sec=None):
        class _R:
            status = 'SUCCEEDED'
            image_urls = [f'https://mock/{task_id}.png']
            seed = seed if False else 42
            message = None

        return _R()

    async def download(self, url, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(PNG_MAGIC + b'0' * 8192)
        return dest


class FakeVideoClient:
    async def submit_i2v(self, **kwargs):
        return 'v1'

    async def wait_task(self, task_id, *, timeout_sec=None):
        class _R:
            status = 'SUCCEEDED'
            video_url = 'https://mock/v.mp4'
            message = None

        return _R()

    async def download(self, url, dest: Path):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b'0' * 150_000)
        return dest


def build_form_state() -> dict:
    state = create_initial_state()
    s = state.sections
    s['customer'].fields['brand'].value = '跃步'
    s['industry'].fields['category'].value = 'shoes'
    s['industry'].fields['subcategory'].value = '国产实战篮球鞋'
    s['industry'].fields['price_band'].value = 'mid'
    s['industry'].fields['positioning'].value = 'mid-high'
    s['industry'].fields['live_type'].value = 'brand'
    s['venue'].fields['area'].value = '20-30'
    s['venue'].fields['window'].value = 'coverable'
    s['venue'].fields['window_pos'].value = 'right'
    s['venue'].fields['renovation'].value = 'minor'
    s['budget'].fields['total'].value = '3-5w'
    s['budget'].fields['equipment'].value = '1-2w'
    s['budget'].fields['decor'].value = '5k-1w'
    s['budget'].fields['flex'].value = 'some'
    s['budget'].fields['has_existing'].value = 'no'
    s['product'].fields['main'].value = '实战篮球鞋'
    s['product'].fields['keywords'].value = '缓震、抓地、透气、街头'
    s['product'].fields['size_cat'].value = 'medium'
    s['host'].fields['count'].value = '1'
    s['host'].fields['movement'].value = 'occasional'
    s['goal'].fields['core'].value = 'new'
    s['goal'].fields['focus'].value = ['product-quality', 'pro-lighting']
    s['goal'].fields['need_3d'].value = 'no'
    s['goal'].fields['deadline'].value = '2w'
    return to_dict(state)


async def main() -> int:
    db.init_db()
    form = build_form_state()
    user_id = db.create_user(f'mockfull_{int(time.time())}', 'h', role='user')
    session_id = db.create_session(user_id, form)
    run_id = db.create_pipeline_run(session_id=session_id, user_id=user_id)
    print(f'pipeline_run_id={run_id}', flush=True)

    t0 = time.time()
    detail = await run_pipeline(
        run_id,
        form_state=form,
        image_client=FakeImageClient(),
        video_client=FakeVideoClient(),
    )
    print(f'elapsed_sec={time.time() - t0:.1f}', flush=True)
    print(f"raw_status={detail.get('raw_status')}", flush=True)
    print(f"skills={detail.get('skills')}", flush=True)
    print(f"error={detail.get('error')}", flush=True)
    print(f"total_cost_cny={detail.get('total_cost_cny')}", flush=True)
    print(f"images={[i.get('angle') for i in detail.get('images') or [] if not i.get('missing')]}", flush=True)
    print(f"video={detail.get('video')}", flush=True)
    print(f"packageFileCount={detail.get('packageFileCount')}", flush=True)

    print('\n--- skill_runs ---', flush=True)
    for s in db.list_skill_runs(run_id):
        err = (s.get('error') or '')[:120]
        print(f"{s['skill']:16} {s['status']:20} cost={s.get('cost_cny')} {err}", flush=True)

    pkg = Path('data/artifacts') / run_id / 'package'
    print('\n--- package files ---', flush=True)
    if pkg.is_dir():
        for p in sorted(pkg.rglob('*')):
            if p.is_file():
                print(f'  {p.relative_to(pkg)}  {p.stat().st_size}B', flush=True)
    return 0 if detail.get('raw_status') in {'ready', 'ready_with_warnings'} else 1


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
