"""开发/演示种子数据：每垂类 ≥20 条。

运行：
  cd backend
  QDRANT_URI=memory:// EMBEDDING_PROVIDER=mock .venv/bin/python scripts/seed_knowledge.py
  # 或连 Qdrant
  QDRANT_URI=http://localhost:6333 .venv/bin/python scripts/seed_knowledge.py
  # 或本地嵌入式
  QDRANT_URI=./data/qdrant .venv/bin/python scripts/seed_knowledge.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from knowledge.config import get_config
from knowledge.embedding import get_embedder
from knowledge.ingest import (
    equipment_row,
    ingest_rows,
    scheme_row,
    source_tag,
    vertical_row,
)
from knowledge.store import get_store

SOURCE = source_tag('seed_knowledge.json', 'ics-seed-v1')

INDUSTRIES = ['women', 'men', 'shoes', 'beauty', 'food', 'jewelry', 'home']
ROOM_SIZES = ['small', 'medium', 'large', 'xlarge']
BUDGETS = ['low', 'mid', 'high', 'ultra']
LIVE_TYPES = ['influencer', 'brand', 'factory', 'ip']

BRANDS = {
    '灯光': ['爱图仕', '神牛', '南光'],
    '相机': ['索尼', '佳能', '松下'],
    '镜头': ['索尼', '适马', '腾龙'],
    '声卡': ['森然', '艾肯', '得胜'],
    '支架': ['云腾', '伟峰', '曼富图'],
    '背景': ['丽屏', '色纸', '定制'],
    '采集卡': ['圆刚', '天创恒达', '绿联'],
    '其他': ['绿联', '小米', '品胜'],
}

INDUSTRY_LABEL = {
    'women': '女装',
    'men': '男装',
    'shoes': '鞋靴',
    'beauty': '美妆',
    'food': '食品',
    'jewelry': '珠宝',
    'home': '家居',
}


def _equipment_rows() -> list[dict]:
    rows: list[dict] = []
    categories = list(BRANDS.keys())
    # 3 垂类 × 每类约 8 设备 ≈ 演示规模；再补 all 通用
    idx = 0
    for industry in INDUSTRIES:
        for room in ROOM_SIZES:
            for budget in BUDGETS:
                category = categories[idx % len(categories)]
                brand = BRANDS[category][idx % len(BRANDS[category])]
                name = f'{brand}{INDUSTRY_LABEL[industry]}专用{category}{idx + 1}号'
                text = (
                    f'{name}，{category}设备，适用{INDUSTRY_LABEL[industry]}直播间，'
                    f'{room}空间，{budget}预算档，支持三点布光与快速拆装。'
                )
                rows.append(
                    equipment_row(
                        name=name,
                        category=category,
                        brand=brand,
                        price_band=budget,
                        room_size=room,
                        industry=industry,
                        specs={
                            'power_w': 100 + (idx % 5) * 50,
                            'color_temp_k': 5600,
                            'notes': f'{INDUSTRY_LABEL[industry]}场景推荐',
                        },
                        text=text,
                        source=SOURCE,
                    )
                )
                idx += 1
    # 通用条目
    for i in range(10):
        category = categories[i % len(categories)]
        brand = BRANDS[category][0]
        name = f'通用{category}套装{i + 1}'
        text = f'{name}，跨垂类通用{category}，适合中小型直播间基础搭建，性价比优先。'
        rows.append(
            equipment_row(
                name=name,
                category=category,
                brand=brand,
                price_band=BUDGETS[i % 4],
                room_size=ROOM_SIZES[i % 4],
                industry='all',
                specs={'kit': True},
                text=text,
                source=SOURCE,
            )
        )
    return rows


def _scheme_rows(equipment_ids: list[int]) -> list[dict]:
    rows: list[dict] = []
    idx = 0
    for industry in INDUSTRIES:
        for room in ROOM_SIZES:
            for budget in BUDGETS:
                live = LIVE_TYPES[idx % len(LIVE_TYPES)]
                name = f'{INDUSTRY_LABEL[industry]} {room} {budget}档{live}方案'
                picked = equipment_ids[idx % len(equipment_ids) : idx % len(equipment_ids) + 5]
                text = (
                    f'{name}：三点布光 + 背景层次 + 单主机位，'
                    f'针对{INDUSTRY_LABEL[industry]}商品质感优化，预算档 {budget}。'
                )
                rows.append(
                    scheme_row(
                        scheme_name=name,
                        industry=industry,
                        budget_level=budget,
                        room_size=room,
                        live_type=live,
                        equipment_ids=picked,
                        package_tiers=[
                            {
                                'tier': 'basic',
                                'total_price_range': '8k-1.5w',
                                'items': picked[:2],
                            },
                            {
                                'tier': 'standard',
                                'total_price_range': '1.5w-3w',
                                'items': picked[:3],
                            },
                            {
                                'tier': 'premium',
                                'total_price_range': '3w-6w',
                                'items': picked,
                            },
                        ],
                        layout_notes=f'{INDUSTRY_LABEL[industry]}直播间建议保留 1.2m 讲解动线，背景距商品 1.5m。',
                        text=text,
                        source=SOURCE,
                    )
                )
                idx += 1
    return rows


def _vertical_rows() -> list[dict]:
    tips = {
        'women': [
            ('布光', '女装直播间强调面料垂感与色准。主灯 45° 侧上，辅灯补阴影，背景灯拉开层次。色温统一 5600K，避免偏色导致退货。'),
            ('背景', '女装背景宜简洁高级：莫兰迪色墙 + 一盏轮廓光。避免高饱和撞色抢商品视觉。小空间可用 1.8m 背景布折叠收纳。'),
            ('机位', '主机位胸口高度俯角 5°，展示全身；细节机位对准面料纹理。转身展示时主播与镜头保持 1.2m。'),
            ('商品展示', '女装讲解顺序：整体版型 → 面料特写 → 穿搭场景。手持衣架旋转 15° 可提升停留。'),
            ('话术区', '话术提词器置于镜头正下方 15°，字号保证 2m 外可读。价格牌与优惠信息固定右下角安全区。'),
        ],
        'men': [
            ('布光', '男装强调轮廓与质感，主灯略高，侧逆光勾勒肩线。避免正面平光导致版型扁平。'),
            ('背景', '工业风水泥墙或深灰模块墙，突出服装线条。灯光打亮背景 1-2 档，拉开前后景。'),
            ('机位', '主机位略低，增强气场。裤装展示增加下移机位，鞋履特写单独机位。'),
            ('商品展示', '正装讲版型与场合，休闲讲面料克重。折叠演示比悬挂更易传达厚度。'),
            ('话术区', '信息密度可略低于女装，强调参数与场景。尺码对照表常驻画面一角。'),
        ],
        'shoes': [
            ('布光', '鞋靴直播间强调鞋面色准与中底层次。主灯 45° 侧上，侧逆光勾勒轮廓与鞋面材质；镜面地台控反射。色温统一 4500K，避免跑鞋荧光色偏色导致退货。'),
            ('背景', '双层鞋墙 + 鞋盒堆叠建立真实仓播层次，深灰工业风模块墙配橙色点缀灯带。避免高饱和背景抢鞋款配色。小空间可用 1.6m 可移动鞋墙架。'),
            ('机位', '主机位半身讲款，细节机位对准鞋面编织/皮革与外底纹路；下移机位拍上脚效果；后侧机位交代鞋墙纵深。主播到镜头保持 1.2m。'),
            ('商品展示', '鞋靴讲解顺序：整体廓形 → 鞋面材质特写 → 中底/外底 → 上脚试穿。亚克力旋转鞋台慢速转动 360° 展示；换鞋凳固定在主机位右侧 45°。'),
            ('话术区', '尺码对照表与脚型建议常驻右下角。缓震/抓地/透气等参数卡固定一角，高客单鞋款客服入口不可遮挡。'),
        ],
        'beauty': [
            ('布光', '美妆要求极高显色指数 CRI≥95。主灯大柔光箱，面部测光准确，避免过曝高光。'),
            ('背景', '浅色纯净背景突出产品瓶身。金属与玻璃材质需控制反射，可用偏振技巧。'),
            ('机位', '面部特写机位固定，手臂试色机位略高。口红/眼影需微距或手机补充。'),
            ('商品展示', '先质地后上脸。粉底液在手背推开，口红先唇形后抿纸。灯光下前后对比最有说服力。'),
            ('话术区', '成分与功效话术卡。敏感肌提示必须清晰可读，合规标识不可遮挡。'),
        ],
        'food': [
            ('布光', '食品强调食欲：暖色辅助灯 3200-4000K，主灯保持中性以免整体偏色。避免油面过曝。'),
            ('背景', '厨房场景或木质台面。背景不宜过乱，焦点始终在食物。蒸汽可用逆光增强。'),
            ('机位', '主机位 45° 美食机位，特写对准切开截面。包装展示单独正视机位。'),
            ('商品展示', '开箱 → 切开 → 品尝三段式。分量对比用标准餐具参照。'),
            ('话术区', '保质期与储存方式固定角标。过敏原信息不可省略。'),
        ],
        'jewelry': [
            ('布光', '珠宝需点光与黑绒背景突出火彩。主灯硬光 + 反光板补阴影，避免整体雾化。'),
            ('背景', '深色绒布或亚克力展台。旋转展示台转速慢，确保自动对焦跟上。'),
            ('机位', '微距机位必须，主机位半身讲解。手指佩戴特写单独固定机位。'),
            ('商品展示', '证书与材质先讲，再上手佩戴。钻石类在灯下转动展示火彩。'),
            ('话术区', '克重、证书编号、售后政策清晰展示。高客单客服入口常驻。'),
        ],
        'home': [
            ('布光', '家居强调整体氛围：大范围柔光 + 局部重点灯。避免单一顶灯造成压抑。'),
            ('背景', '样板间实景优于纯色背景。家具尺度要与主播形成真实参照。'),
            ('机位', '广角交代空间，中景讲功能，特写讲材质（木纹、布纹、五金）。'),
            ('商品展示', '先场景后单品。演示收纳/变形功能时固定机位拍摄手部。'),
            ('话术区', '尺寸参数表常驻。大件物流与安装说明不可省略。'),
        ],
    }
    rows: list[dict] = []
    for industry, scenes in tips.items():
        for i in range(4):  # 每行业循环技巧，凑满块数
            for scene, content in scenes:
                block = (
                    f'{scene}要点（{INDUSTRY_LABEL[industry]}）\n'
                    f'{content}\n'
                    f'补充：{INDUSTRY_LABEL[industry]}直播间在{scene}环节需结合面积与预算档调整设备功率与数量，'
                    f'小空间控制阴影，大空间保证照度均匀。实操时先定主机位再布光，避免返工。'
                )
                rows.append(
                    vertical_row(
                        industry=industry,
                        scene=scene,
                        content=block,
                        text=block,
                        source=SOURCE,
                        chunk_index=len(rows),
                    )
                )
    return rows


def main() -> None:
    cfg = get_config()
    store = get_store(cfg)
    embedder = get_embedder(cfg)
    store.ensure_collections()

    eq_rows = _equipment_rows()
    n_eq = ingest_rows('equipment_specs', eq_rows, store=store, embedder=embedder, config=cfg)
    # 回读 id（memory store）或用业务 id
    eq_ids = [r['id'] for r in eq_rows]

    scheme = _scheme_rows(eq_ids)
    n_sc = ingest_rows('setup_schemes', scheme, store=store, embedder=embedder, config=cfg)

    vert = _vertical_rows()
    n_vk = ingest_rows('vertical_knowledge', vert, store=store, embedder=embedder, config=cfg)

    print(f'seeded equipment_specs={n_eq} setup_schemes={n_sc} vertical_knowledge={n_vk}')
    print(f'qdrant_uri={cfg.qdrant_uri} embedding={cfg.embedding_provider}')


if __name__ == '__main__':
    main()
