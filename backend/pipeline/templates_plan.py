"""知识库不可用时的预置通用模板方案。"""
from __future__ import annotations

from knowledge.mapping import parse_budget_wan
from pipeline.models import (
    EquipmentItem,
    LayoutPlan,
    LayoutZone,
    PackageItem,
    PackageTier,
    PlanDraft,
    RequirementBrief,
    SceneCard,
)
from pipeline.normalize import industry_label

_INDUSTRY_STYLE = {
    'women': (['高级感', '质感面料', '柔和层次'], ['#f5f0e8', '#2c2c2c', '#c4a574'], '4000K'),
    'men': (['利落', '低饱和', '金属质感'], ['#e8e8e8', '#1a1a1a', '#6b7c8a'], '4000K'),
    'beauty': (['清透', '高显色', '近景质感'], ['#faf7f7', '#d4a5b5', '#ffffff'], '5000K'),
    'food': (['新鲜', '暖光食欲', '近景细节'], ['#fff8f0', '#c45c26', '#f0e6d6'], '3500K'),
    'jewelry': (['璀璨', '深色背景', '高光点缀'], ['#1a1a1a', '#c9a227', '#f5f5f5'], '4000K'),
    'home': (['生活场景', '温暖收纳', '材质对比'], ['#f0ebe3', '#8b7355', '#ffffff'], '3500K'),
    'digital': (['科技感', '冷色光效', '产品特写'], ['#0f1419', '#3d8bfd', '#e8eaed'], '5000K'),
    'baby': (['柔和安全', '圆角家具', '低饱和'], ['#f7f3ee', '#a8c5b5', '#ffffff'], '4000K'),
}
_DEFAULT_STYLE = (['干净', '专业', '可落地'], ['#f5f5f5', '#333333', '#888888'], '4000K')

_ROOM_FIXTURES = {
    'small': (['COB主灯×1', '柔光箱×1', '补光板×1'], ['主播桌', '简易背景架']),
    'medium': (['COB主灯×2', '柔光箱×2', '发丝灯×1'], ['主播桌', '展示架', '背景墙板']),
    'large': (['COB主灯×3', '柔光箱×2', '发丝灯×2', '地灯×1'], ['主播桌', '展示架', '背景墙', '侧柜']),
    'xlarge': (['COB主灯×4', '柔光箱×3', '发丝灯×2', '氛围灯带'], ['主播桌', '多层展示架', '背景墙', '侧柜', '地毯']),
}


def build_template_plan(brief: RequirementBrief) -> PlanDraft:
    """按行业 + 面积档生成可交付的模板方案（未接入知识库）。"""
    styles, palette, color_temp = _INDUSTRY_STYLE.get(brief.industry, _DEFAULT_STYLE)
    if brief.product_keywords:
        styles = list(dict.fromkeys([*brief.product_keywords, *styles]))[:5]

    fixtures, furniture = _ROOM_FIXTURES.get(
        brief.room_size,
        _ROOM_FIXTURES['medium'],
    )

    equipment = [
        EquipmentItem(
            knowledge_id=None,
            category='灯光',
            name='COB 常亮灯（通用）',
            model='通用 150-300W',
            qty=2,
            unit_price_band='mid',
            reason=f'适配 {brief.area_band or brief.room_size}㎡ {industry_label(brief.industry)}场景主光',
            is_custom=True,
        ),
        EquipmentItem(
            knowledge_id=None,
            category='灯光',
            name='柔光箱/柔光罩',
            model='通用 90cm',
            qty=2,
            unit_price_band='low',
            reason='柔化主光，降低硬阴影，提升商品质感',
            is_custom=True,
        ),
        EquipmentItem(
            knowledge_id=None,
            category='相机',
            name='微单相机',
            model='主流全画幅/APS-C',
            qty=1,
            unit_price_band='mid',
            reason='主机位稳定出画，支持长时间直播',
            is_custom=True,
        ),
        EquipmentItem(
            knowledge_id=None,
            category='镜头',
            name='标准变焦镜头',
            model='24-70mm 等效',
            qty=1,
            unit_price_band='mid',
            reason='覆盖半身与商品特写',
            is_custom=True,
        ),
        EquipmentItem(
            knowledge_id=None,
            category='支架',
            name='灯架/三脚架',
            model='通用承重支架',
            qty=3,
            unit_price_band='low',
            reason='固定灯光与相机，保证机位稳定',
            is_custom=True,
        ),
        EquipmentItem(
            knowledge_id=None,
            category='背景',
            name='背景墙/背景布',
            model='按风格定制',
            qty=1,
            unit_price_band='mid',
            reason='建立品牌视觉层次，避免杂乱背景',
            is_custom=True,
        ),
    ]

    owned_models = {item.model.strip() for item in brief.existing_equipment if item.model}
    owned_types = {item.type.strip() for item in brief.existing_equipment if item.type}
    for item in equipment:
        if item.name in owned_types or item.model in owned_models:
            item.already_owned = True

    budget_bounds = parse_budget_wan(brief.budget_total) or (2.0, 4.0)
    low_mid = (budget_bounds[0] * 0.55 + budget_bounds[0] * 0.75) / 2
    mid_mid = (budget_bounds[0] * 0.85 + budget_bounds[1] * 0.95) / 2
    high_mid = (budget_bounds[1] * 0.9 + budget_bounds[1] * 1.1) / 2

    package_tiers = [
        PackageTier(
            tier='性价比',
            total_range=f'{low_mid:.1f}w'.replace('.0w', 'w'),
            items=[
                PackageItem(name='COB 主灯', qty=1),
                PackageItem(name='柔光箱', qty=1),
                PackageItem(name='相机（复用/入门）', qty=1),
                PackageItem(name='支架套装', qty=2),
            ],
        ),
        PackageTier(
            tier='进阶',
            total_range=f'{mid_mid:.1f}w'.replace('.0w', 'w'),
            items=[
                PackageItem(name='COB 主灯', qty=2),
                PackageItem(name='柔光箱', qty=2),
                PackageItem(name='微单相机', qty=1),
                PackageItem(name='标准镜头', qty=1),
                PackageItem(name='背景方案', qty=1),
            ],
        ),
        PackageTier(
            tier='高配',
            total_range=f'{high_mid:.1f}w'.replace('.0w', 'w'),
            items=[
                PackageItem(name='COB 主灯', qty=3),
                PackageItem(name='柔光箱 + 发丝灯', qty=3),
                PackageItem(name='全画幅相机', qty=1),
                PackageItem(name='镜头组', qty=2),
                PackageItem(name='全案背景与展示', qty=1),
            ],
        ),
    ]

    risks = []
    if brief.window and brief.window != 'none':
        pos_label = {
            'front': '正面',
            'behind': '背后',
            'left': '左侧',
            'right': '右侧',
        }.get(brief.window_pos, '未标明位置')
        risks.append(f'场地存在窗户（{pos_label}），需遮光处理避免杂光')
    if brief.renovation == 'none':
        risks.append('场地不允许装修改动，背景方案优先使用可拆卸材料')
    if brief.budget_flex == 'tight':
        risks.append('预算弹性紧张，套餐金额需严格控制在区间内')
    if brief.existing_equipment:
        risks.append('已有设备需现场核对兼容性（接口、色温、承重）后再定最终清单')
    if brief.missing_core_fields:
        risks.append('部分核心需求信息不完整，方案细节可能需复核')

    steps = [
        '第1步：确认场地尺寸与窗户位置，完成遮光与基础动线规划。',
        '第2步：按主机位、商品区、背景区划分功能分区，固定三脚架与灯架点位。',
        '第3步：安装 COB 主灯与柔光箱，完成三点布光并微调光比。',
        '第4步：架设相机与采集链路，校准白平衡、曝光与对焦距离。',
        '第5步：布置背景层次与商品展示位，完成试播画面验收。',
    ]

    host_note = f'{brief.host_count} 位主播' if brief.host_count else '单主播'
    movement_note = {
        'sit': '以坐姿为主，机位可更近',
        'occasional': '偶尔站起，预留小幅活动空间',
        'frequent': '经常走动，需更大景别与跟拍余量',
        'wide': '大范围移动，建议增加辅助机位与更大布光覆盖',
    }.get(brief.host_movement, '默认站姿半身构图')

    return PlanDraft(
        meta={
            'brand': brief.brand,
            'industry': brief.industry,
            'room_size': brief.room_size,
            'budget_total': brief.budget_total,
            'generated_at': '',
            'pipeline_run_id': '',
            'knowledge_refs': [],
            'completeness': brief.completeness,
            'status_flags': ['knowledge_unavailable', 'template_plan'],
        },
        summary=(
            f'{brief.brand or "客户"}｜{industry_label(brief.industry)}'
            f'{("｜" + brief.subcategory) if brief.subcategory else ""} '
            f'{brief.room_size} 直播间搭建方案（模板版）'
        ),
        layout=LayoutPlan(
            zones=[
                LayoutZone(name='主播区', notes=f'{host_note}；{movement_note}'),
                LayoutZone(name='商品展示区', notes=f'围绕主营「{brief.product_main or "商品"}」布置近景展示位'),
                LayoutZone(name='背景区', notes='建立 2–3 层视觉层次，避免单调平面'),
            ],
            lighting_plan='三点布光：主灯 45° 副灯补光 + 发丝灯勾边；色温统一 4000K 左右。',
            camera_plan='主机位正面半身；副机位左侧 45° 补商品特写；预留后侧纵深位。',
            background_plan='背景与品牌关键词对齐，控制 logo 与杂乱元素入画。',
        ),
        equipment_list=equipment,
        package_tiers=package_tiers,
        setup_steps=steps,
        risks=risks,
        scene_card=SceneCard(
            room_size_band=brief.room_size,
            style_keywords=styles,
            color_palette=palette,
            color_temp=color_temp,
            furniture=furniture,
            lighting_fixtures=fixtures,
            product_category=brief.product_main or industry_label(brief.industry),
            camera_angles=['front', 'left', 'rear'],
            forbidden=['文字水印', '品牌logo', '杂乱电线入画'],
        ),
    )
