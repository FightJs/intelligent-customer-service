"""清理旧女装/云裳演示管线，并用鞋类示例重跑真实全链路。

运行：cd backend && .venv/bin/python scripts/replace_demo_with_shoes.py
"""
from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)

from dotenv import load_dotenv

load_dotenv(BACKEND / '.env', override=True)

import sqlite3  # noqa: E402

from store import db  # noqa: E402
from survey.state import create_initial_state, to_dict  # noqa: E402
from pipeline.orchestrator import run_pipeline  # noqa: E402


def build_shoe_form_state() -> dict:
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


def cleanup_yunshang_runs() -> int:
    """删除云裳/女装相关的 pipeline 及产物目录。"""
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(
            '''
            SELECT r.id, r.session_id
            FROM pipeline_runs r
            LEFT JOIN sessions s ON s.session_id = r.session_id
            WHERE COALESCE(s.form_state, '') LIKE '%云裳%'
               OR COALESCE(s.form_state, '') LIKE '%women%'
               OR COALESCE(s.form_state, '') LIKE '%香云纱%'
               OR COALESCE(s.form_state, '') LIKE '%连衣裙%'
            '''
        ).fetchall()
        run_ids = [r['id'] for r in rows]
        if not run_ids:
            print('未发现云裳/女装管线记录')
            return 0

        for rid in run_ids:
            conn.execute('DELETE FROM artifacts WHERE pipeline_run_id = ?', (rid,))
            conn.execute('DELETE FROM skill_runs WHERE pipeline_run_id = ?', (rid,))
            conn.execute('DELETE FROM pipeline_runs WHERE id = ?', (rid,))
            art_dir = Path('data/artifacts') / rid
            if art_dir.exists():
                shutil.rmtree(art_dir, ignore_errors=True)
            print(f'已删除管线 {rid}')

        # 清理无管线引用的云裳 sessions（可选，避免摘要读到旧表单）
        conn.execute(
            '''
            DELETE FROM sessions
            WHERE form_state LIKE '%云裳%'
              AND session_id NOT IN (SELECT session_id FROM pipeline_runs)
            '''
        )
        conn.commit()
        print(f'共清理 {len(run_ids)} 条旧管线')
        return len(run_ids)
    finally:
        conn.close()


async def run_shoe_pipeline() -> int:
    db.init_db()
    form = build_shoe_form_state()
    username = f'shoedemo_{int(time.time())}'
    user_id = db.create_user(username, 'h', role='user')
    session_id = db.create_session(user_id, form)
    run_id = db.create_pipeline_run(session_id=session_id, user_id=user_id)
    print(f'pipeline_run_id={run_id}', flush=True)
    print(f'user_id={user_id} username={username}', flush=True)

    t0 = time.time()
    detail = await run_pipeline(run_id, form_state=form)
    print(f'elapsed_sec={time.time() - t0:.1f}', flush=True)
    print(f"title={detail.get('title')}", flush=True)
    print(f"industry={detail.get('industry')}", flush=True)
    print(f"status={detail.get('status')} raw={detail.get('raw_status')}", flush=True)
    print(f"skills={detail.get('skills')}", flush=True)
    print(f"images={detail.get('images')}", flush=True)
    print(f"video={detail.get('video')}", flush=True)
    print(f"error={detail.get('error')}", flush=True)

    plan_json = Path('data/artifacts') / run_id / 'docs' / 'plan.json'
    if plan_json.exists():
        import json

        data = json.loads(plan_json.read_text(encoding='utf-8'))
        sc = data.get('scene_card') or {}
        print('--- scene_card ---', flush=True)
        print(f"product={sc.get('product_category')}", flush=True)
        print(f"style={sc.get('style_keywords')}", flush=True)
        print(f"furniture={sc.get('furniture')}", flush=True)

    return 0 if detail.get('raw_status') in {'ready', 'ready_with_warnings'} else 1


async def main() -> int:
    cleanup_yunshang_runs()
    return await run_shoe_pipeline()


if __name__ == '__main__':
    raise SystemExit(asyncio.run(main()))
