"""知识库不可用时的预置通用模板方案。

设备型号使用直播行业常见在售/在租型号，便于直接询价与租赁。
不编造具体小店名；租赁渠道使用全国性平台与本地渠道类型。
"""
from __future__ import annotations

from typing import Any

from knowledge.mapping import parse_budget_wan
from pipeline.models import (
    EquipmentItem,
    LayoutPlan,
    LayoutZone,
    PackageItem,
    PackageTier,
    PlanDraft,
    RentalChannel,
    RequirementBrief,
    SceneCard,
)
from pipeline.normalize import industry_label

_INDUSTRY_STYLE = {
    'women': (['高级感', '质感面料', '柔和层次'], ['#f5f0e8', '#2c2c2c', '#c4a574'], '4000K'),
    'men': (['利落', '低饱和', '金属质感'], ['#e8e8e8', '#1a1a1a', '#6b7c8a'], '4000K'),
    'shoes': (['街头工业风', '鞋墙陈列', '高对比质感'], ['#1c1c1e', '#f2f2f2', '#ff6b2c'], '4500K'),
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

_ROOM_SCALE = {
    'small': {'area': '10-20㎡', 'ceiling': '≥2.6m', 'power': '单相 2.5kW', 'hosts': '1 机位 / 1 主播'},
    'medium': {'area': '20-35㎡', 'ceiling': '≥2.8m', 'power': '单相 4kW 或分路供电', 'hosts': '2 机位 / 1-2 主播'},
    'large': {'area': '35-60㎡', 'ceiling': '≥3.0m', 'power': '分路 6kW+，灯光独立回路', 'hosts': '3 机位 / 1-2 主播 + 助播'},
    'xlarge': {'area': '60㎡+', 'ceiling': '≥3.2m', 'power': '分路 8kW+，建议三相进线', 'hosts': '多机位 / 多主播动线'},
}

_SHOE_FURNITURE = [
    '双层鞋墙展示架',
    '亚克力旋转鞋台',
    '换鞋凳',
    '镜面地台',
    '鞋盒堆叠陈列',
    '地面地贴动线',
]

# 规格字段展示顺序
_SPEC_ORDER = ['功率', '色温', '显色', '传感器', '画幅', '焦段', '光圈', '接口', '分辨率', '承重', '尺寸', '备注']

_RENTAL_CHANNELS = [
    RentalChannel(
        name='人人租机',
        kind='platform',
        note='全国器材租赁平台，按周/月租，适合相机、灯光整套试跑',
        categories=['相机', '镜头', '灯光', '采集卡'],
    ),
    RentalChannel(
        name='京东企业购 / 京东租赁',
        kind='ecom',
        note='可开专票，适合品牌方采购；部分品类支持以租代购',
        categories=['相机', '灯光', '支架', '背景', '其他'],
    ),
    RentalChannel(
        name='天猫 / 淘宝品牌旗舰店',
        kind='ecom',
        note='官方质保齐全，适合必买设备与耗材长期持有',
        categories=['灯光', '声卡', '支架', '背景'],
    ),
    RentalChannel(
        name='本地摄影器材城 / 影棚租赁',
        kind='local',
        note='可现场试光试机，当日取还；灯光与背景板租赁性价比高',
        categories=['灯光', '相机', '镜头', '背景'],
    ),
    RentalChannel(
        name='品牌官方渠道（爱图仕 / 神牛 / 索尼等）',
        kind='brand',
        note='原厂售后与固件支持，长期持有首选',
        categories=['灯光', '相机', '镜头'],
    ),
]


def _eq(
    category: str,
    name: str,
    *,
    brand: str,
    model: str,
    qty: int,
    band: str,
    reason: str,
    must_buy: bool,
    specs: dict[str, Any],
    purchase_price: str,
    rent_monthly: str,
) -> EquipmentItem:
    return EquipmentItem(
        knowledge_id=None,
        category=category,
        name=name,
        model=model,
        brand=brand,
        qty=qty,
        unit_price_band=band,
        reason=reason,
        is_custom=True,
        must_buy=must_buy,
        specs=specs,
        purchase_price=purchase_price,
        rent_monthly=rent_monthly,
    )


def _equipment_for_room(room_size: str, industry: str, area_label: str) -> list[EquipmentItem]:
    small = room_size == 'small'
    large = room_size in {'large', 'xlarge'}

    # 主灯：小间 100-150W，中大间 200-300W
    if small:
        main_light = _eq(
            '灯光', 'LED COB 常亮主灯',
            brand='爱图仕', model='Aputure 100d',
            qty=1, band='mid',
            reason=f'{area_label} 单主灯足够压住主播与商品，5600K 日光色温统一',
            must_buy=True,
            specs={'功率': '100W', '色温': '5600K', '显色': 'CRI 96+ / TLCI 96+', '备注': 'Bowens 卡口，兼容主流柔光箱'},
            purchase_price='¥1,800-2,400',
            rent_monthly='¥150-250',
        )
        fill_light = _eq(
            '灯光', '双色温平板补光灯',
            brand='南光', model='Forza 60B II',
            qty=1, band='low',
            reason='补光/发丝光，双色温应对肤色与商品色差',
            must_buy=True,
            specs={'功率': '60W', '色温': '2700-6500K', '显色': 'CRI 95+', '尺寸': '便携灯体'},
            purchase_price='¥1,200-1,600',
            rent_monthly='¥100-180',
        )
    elif large:
        main_light = _eq(
            '灯光', 'LED COB 常亮主灯',
            brand='爱图仕', model='Aputure 300d II',
            qty=2, band='high',
            reason=f'{area_label} 大空间需 300W 级主灯保证主播走动后仍不掉光',
            must_buy=True,
            specs={'功率': '300W', '色温': '5600K', '显色': 'CRI 96+', '备注': '支持 Sidus Link 无线控光'},
            purchase_price='¥4,500-6,000/台',
            rent_monthly='¥400-600/台',
        )
        fill_light = _eq(
            '灯光', 'COB 副灯 / 侧补光',
            brand='神牛', model='SL150IIIBi',
            qty=1, band='mid',
            reason='侧补与商品特写光，双色温校准肤色',
            must_buy=True,
            specs={'功率': '150W', '色温': '2800-6500K', '显色': 'CRI 96+', '接口': 'Bowens'},
            purchase_price='¥1,600-2,200',
            rent_monthly='¥180-280',
        )
    else:
        main_light = _eq(
            '灯光', 'LED COB 常亮主灯',
            brand='爱图仕', model='Aputure 200d',
            qty=2, band='mid',
            reason=f'{area_label} 中型间双主灯覆盖主播区与商品区',
            must_buy=True,
            specs={'功率': '200W', '色温': '5600K', '显色': 'CRI 96+', '备注': '风扇静音，适合长时间直播'},
            purchase_price='¥2,800-3,600/台',
            rent_monthly='¥250-380/台',
        )
        fill_light = _eq(
            '灯光', '双色温 COB 补光',
            brand='神牛', model='SL60IIIBi',
            qty=1, band='low',
            reason='低成本补光与发丝光，双色温微调',
            must_buy=False,
            specs={'功率': '70W', '色温': '2800-6500K', '显色': 'CRI 95+', '尺寸': '桌面/灯架两用'},
            purchase_price='¥700-1,000',
            rent_monthly='¥80-140',
        )

    softbox = _eq(
        '灯光', '深口抛物线柔光箱',
        brand='神牛', model='QR-P90（90cm）',
        qty=2 if not small else 1, band='low',
        reason='柔化主光、压硬阴影，商品质感关键附件',
        must_buy=True,
        specs={'尺寸': '90cm 深口', '备注': '配格栅更控光，鞋服/珠宝必配'},
        purchase_price='¥280-450',
        rent_monthly='¥30-60',
    )

    if industry in {'jewelry', 'beauty', 'digital'}:
        camera = _eq(
            '相机', '全画幅微单（主机位）',
            brand='索尼', model='ILCE-7M4（A7M4）',
            qty=1, band='high',
            reason='高感与对焦适合近景质感；美妆/珠宝/数码细节要求高',
            must_buy=True,
            specs={'传感器': '全画幅 33MP', '画幅': '全画幅', '接口': 'HDMI 干净输出 + USB 供电', '备注': '支持长时间录制不过热（注意散热）'},
            purchase_price='¥14,000-16,500',
            rent_monthly='¥800-1,200',
        )
        lens = _eq(
            '镜头', '标准变焦 + 微距补充',
            brand='适马', model='24-70mm F2.8 DG DN + 90mm 微距',
            qty=1, band='high',
            reason='变焦覆盖半身讲款，微距拍材质/色号/接口细节',
            must_buy=True,
            specs={'焦段': '24-70mm / 90mm', '光圈': 'F2.8 / F2.8', '备注': '珠宝/美妆强烈建议微距'},
            purchase_price='¥6,500-9,000',
            rent_monthly='¥350-550',
        )
    else:
        camera = _eq(
            '相机', 'APS-C 微单（主机位）',
            brand='索尼', model='ZV-E10',
            qty=1, band='mid',
            reason='性价比主机位，产品展示模式与背景虚化一键可用',
            must_buy=True,
            specs={'传感器': 'APS-C 24.2MP', '画幅': 'APS-C', '接口': 'Micro HDMI + USB-C', '备注': '需假电池持续供电'},
            purchase_price='¥4,500-5,500',
            rent_monthly='¥280-400',
        )
        if large:
            camera = _eq(
                '相机', '全画幅微单（主机位）',
                brand='佳能', model='EOS R6 Mark II',
                qty=1, band='high',
                reason='大景别跟拍与长时间直播稳定性更好',
                must_buy=True,
                specs={'传感器': '全画幅 24.2MP', '画幅': '全画幅', '接口': 'HDMI 清晰输出', '备注': '双卡槽备份更安心'},
                purchase_price='¥13,000-15,500',
                rent_monthly='¥750-1,100',
            )
        lens = _eq(
            '镜头', '标准变焦镜头',
            brand='适马', model='18-50mm F2.8 DC DN',
            qty=1, band='mid',
            reason='覆盖半身与商品特写，轻便适合固定机位',
            must_buy=True,
            specs={'焦段': '18-50mm', '光圈': 'F2.8 恒定', '备注': 'APS-C 等效约 27-75mm'},
            purchase_price='¥3,200-3,800',
            rent_monthly='¥180-280',
        )

    capture = _eq(
        '采集卡', 'HDMI 采集卡',
        brand='圆刚', model='Live Gamer Mini (GC311)',
        qty=1, band='mid',
        reason='相机 HDMI 进电脑推流，延迟低、兼容主流推流软件',
        must_buy=True,
        specs={'分辨率': '1080p60', '接口': 'HDMI in / USB 3.0', '备注': '品牌直播常用入门卡'},
        purchase_price='¥600-900',
        rent_monthly='¥60-100',
    )

    audio = _eq(
        '声卡', '直播声卡 + 电容麦',
        brand='森然', model='播吧 GT3 + 电容麦套装',
        qty=1, band='mid',
        reason='人声清晰是转化基础；支持监听与音效',
        must_buy=True,
        specs={'接口': 'USB / 3.5mm 监听', '备注': '套装含防喷罩与支架更省事'},
        purchase_price='¥1,200-2,000',
        rent_monthly='¥120-200',
    )

    stand = _eq(
        '支架', '灯架 / 三脚架套装',
        brand='曼富图', model='MT055 三脚架 + 神牛 3m 灯架',
        qty=3, band='low',
        reason='固定灯光与相机，承重与高度决定布光自由度',
        must_buy=True,
        specs={'承重': '三脚架 8kg+ / 灯架 5kg+', '尺寸': '灯架最高约 3m'},
        purchase_price='¥900-1,800（套）',
        rent_monthly='¥80-150（套）',
    )

    background = _eq(
        '背景', '背景墙 / 模块背景',
        brand='丽屏', model='模块化背景墙 + 品牌色板',
        qty=1, band='mid',
        reason='建立品牌视觉层次；可拆卸适配短租场地',
        must_buy=False,
        specs={'尺寸': f'按 {area_label} 定制', '备注': '优先哑光面，减少反光穿帮'},
        purchase_price='¥1,500-6,000',
        rent_monthly='¥200-600',
    )

    items = [main_light, fill_light, softbox, camera, lens, capture, audio, stand, background]

    if industry == 'shoes':
        items.append(_eq(
            '背景', '鞋墙展示架 + 旋转鞋台',
            brand='定制', model='双层鞋墙 + 亚克力转台',
            qty=1, band='mid',
            reason='鞋靴垂类核心陈列：上脚动线 + 鞋底细节展示',
            must_buy=False,
            specs={'尺寸': '鞋墙宽 1.8-2.4m', '备注': '转台承重 ≥15kg'},
            purchase_price='¥2,000-5,000',
            rent_monthly='¥250-500',
        ))
    if industry in {'food', 'home'}:
        items.append(_eq(
            '其他', '近景特写机位（手机支架）',
            brand='云腾', model='液压云台手机支架',
            qty=1, band='low',
            reason='食品/家居常用手机近景补机位，成本低',
            must_buy=False,
            specs={'承重': '3kg', '备注': '配补光夹更佳'},
            purchase_price='¥150-300',
            rent_monthly='—',
        ))

    return items


def _vertical_notes(industry: str, product_main: str) -> list[str]:
    product = product_main or '主营商品'
    table = {
        'women': [
            f'女装直播间以「{product}」面料垂坠与上身版型为核心，主光建议 45° 侧上，避免平光压扁质感。',
            '色温 4000K 左右更接近日常试衣间观感；深色款需单独补侧光提轮廓。',
            '试衣/换装区建议用帘子或移动屏风隔断，避免推流穿帮。',
        ],
        'shoes': [
            f'鞋靴直播重点展示「{product}」鞋面材质、中底科技与上脚比例，建议下移机位 + 旋转鞋台。',
            '镜面地台能强化鞋底纹路，但必须控反射：主灯加格栅，避免灯体入镜。',
            '色温建议 4500K，保证鞋面色准；库存堆叠可增强仓播真实感。',
        ],
        'beauty': [
            f'美妆试色对显色要求极高，灯具 CRI≥95，色温统一 5000K 便于对比色号「{product}」。',
            '近景建议 50-100mm 微距或手机近摄，展示粉质/唇釉质地。',
            '背景避免高饱和色抢妆容；白色/浅灰哑光背景最稳。',
        ],
        'food': [
            f'食品直播靠暖光激发食欲，主光 3500K，特写「{product}」时拉高亮度与对比。',
            '近景拍冒汁/拉丝等动态，快门与灯光频闪需匹配（常亮灯优先）。',
            '桌面保持简洁，道具只保留与商品相关的餐具/包装。',
        ],
        'jewelry': [
            f'珠宝反光复杂，用大面积柔光 + 侧逆光勾勒「{product}」金属与刻面火彩。',
            '深色背景更出彩；禁用直射硬光避免死白高光。',
            '微距镜头 + 黑绒托盘是标配；注意手指入画整洁。',
        ],
        'home': [
            f'家居场景化直播，围绕「{product}」使用动线搭景，多用材质对比（木、布、金属）。',
            '中性暖光 3500K，展示收纳与尺寸时配卷尺/参照物。',
            '可多机位：全景交代空间，近景拍细节与使用方式。',
        ],
        'digital': [
            f'数码产品侧重接口、屏幕与工艺细节，冷色光 5000K + 局部高光「{product}」。',
            '防反光：屏幕类商品降低主灯角度，使用偏振思路控眩光。',
            '对比环节准备竞品尺寸参照，增强说服力。',
        ],
        'baby': [
            f'母婴直播强调安全与柔和，低饱和配色，圆角道具，光比控制小。',
            f'「{product}」展示材质与认证信息时用近景 + 字卡辅助。',
            '避免强对比闪烁光；环境音干净，声学处理优先。',
        ],
    }
    return table.get(industry, [
        f'围绕「{product}」建立 2-3 层背景层次，主灯 45°、副灯补阴影、发丝灯勾边。',
        '色温全链路统一，相机白平衡手动锁定，避免自动漂移。',
        '试播 10 分钟检查穿帮元素：电线、反光灯体、杂乱 logo。',
    ])


def build_template_plan(brief: RequirementBrief) -> PlanDraft:
    """按行业 + 面积档生成可交付的模板方案（未接入知识库）。"""
    styles, palette, color_temp = _INDUSTRY_STYLE.get(brief.industry, _DEFAULT_STYLE)
    if brief.product_keywords:
        styles = list(dict.fromkeys([*brief.product_keywords, *styles]))[:5]

    fixtures, furniture = _ROOM_FIXTURES.get(
        brief.room_size,
        _ROOM_FIXTURES['medium'],
    )
    if brief.industry == 'shoes':
        furniture = list(dict.fromkeys([*_SHOE_FURNITURE, *furniture]))

    area_label = brief.area_band or brief.room_size
    equipment = _equipment_for_room(brief.room_size, brief.industry, area_label)

    owned_models = {item.model.strip() for item in brief.existing_equipment if item.model}
    owned_types = {item.type.strip() for item in brief.existing_equipment if item.type}
    for item in equipment:
        if item.name in owned_types or item.model in owned_models:
            item.already_owned = True
            item.must_buy = False

    must_buy_list = [
        f'{item.brand} {item.model}'.strip() or item.name
        for item in equipment
        if item.must_buy and not item.already_owned
    ]

    budget_bounds = parse_budget_wan(brief.budget_total) or (2.0, 4.0)
    low_mid = (budget_bounds[0] * 0.55 + budget_bounds[0] * 0.75) / 2
    mid_mid = (budget_bounds[0] * 0.85 + budget_bounds[1] * 0.95) / 2
    high_mid = (budget_bounds[1] * 0.9 + budget_bounds[1] * 1.1) / 2

    def _fmt_wan(v: float) -> str:
        return f'{v:.1f}w'.replace('.0w', 'w')

    # 按设备真实型号组装三档套餐（租 / 买双视角）
    mid_cam = next(e for e in equipment if e.category == '相机')
    mid_light = next(e for e in equipment if e.category == '灯光' and e.must_buy)
    mid_soft = next(e for e in equipment if '柔光' in e.name)
    mid_capture = next(e for e in equipment if e.category == '采集卡')
    mid_audio = next(e for e in equipment if e.category == '声卡')
    mid_stand = next(e for e in equipment if e.category == '支架')
    mid_bg = next(e for e in equipment if e.category == '背景')

    package_tiers = [
        PackageTier(
            tier='性价比',
            total_range=_fmt_wan(low_mid),
            mode='mixed',
            monthly_rent_range=f'{max(300, int(low_mid * 800))}-{max(500, int(low_mid * 1200))} 元/月',
            suitable='预算优先：灯光与相机租赁，采集/声卡自购',
            items=[
                PackageItem(name=f'{mid_light.brand} {mid_light.model}', qty=1, model=mid_light.model, brand=mid_light.brand),
                PackageItem(name=f'{mid_soft.brand} {mid_soft.model}', qty=1, model=mid_soft.model, brand=mid_soft.brand),
                PackageItem(name=f'{mid_cam.brand} {mid_cam.model}', qty=1, model=mid_cam.model, brand=mid_cam.brand),
                PackageItem(name=f'{mid_capture.brand} {mid_capture.model}', qty=1, model=mid_capture.model, brand=mid_capture.brand),
                PackageItem(name=f'{mid_stand.brand} 支架套装', qty=2, model=mid_stand.model, brand=mid_stand.brand),
            ],
        ),
        PackageTier(
            tier='进阶',
            total_range=_fmt_wan(mid_mid),
            mode='mixed',
            monthly_rent_range=f'{max(600, int(mid_mid * 700))}-{max(900, int(mid_mid * 1000))} 元/月',
            suitable='主力档：双主灯 + 微单，灯光可租、相机半租半买',
            items=[
                PackageItem(name=f'{mid_light.brand} {mid_light.model}', qty=2 if mid_light.qty >= 2 else 1, model=mid_light.model, brand=mid_light.brand),
                PackageItem(name=f'{mid_soft.brand} {mid_soft.model}', qty=2, model=mid_soft.model, brand=mid_soft.brand),
                PackageItem(name=f'{mid_cam.brand} {mid_cam.model}', qty=1, model=mid_cam.model, brand=mid_cam.brand),
                PackageItem(name=f'{mid_capture.brand} {mid_capture.model}', qty=1, model=mid_capture.model, brand=mid_capture.brand),
                PackageItem(name=f'{mid_audio.brand} {mid_audio.model}', qty=1, model=mid_audio.model, brand=mid_audio.brand),
                PackageItem(name=f'{mid_bg.brand} {mid_bg.model}', qty=1, model=mid_bg.model, brand=mid_bg.brand),
            ],
        ),
        PackageTier(
            tier='高配',
            total_range=_fmt_wan(high_mid),
            mode='buy',
            monthly_rent_range='适合整套购置；灯光可先租后买',
            suitable='长期自播/品牌自播：全画幅 + 三灯体系全买',
            items=[
                PackageItem(name=f'{mid_light.brand} {mid_light.model}', qty=3, model=mid_light.model, brand=mid_light.brand),
                PackageItem(name=f'{mid_soft.brand} {mid_soft.model}', qty=3, model=mid_soft.model, brand=mid_soft.brand),
                PackageItem(name=f'{mid_cam.brand} {mid_cam.model}', qty=1, model=mid_cam.model, brand=mid_cam.brand),
                PackageItem(name=f'{mid_capture.brand} {mid_capture.model}', qty=1, model=mid_capture.model, brand=mid_capture.brand),
                PackageItem(name=f'{mid_audio.brand} {mid_audio.model}', qty=1, model=mid_audio.model, brand=mid_audio.brand),
                PackageItem(name=f'{mid_bg.brand} {mid_bg.model}', qty=1, model=mid_bg.model, brand=mid_bg.brand),
                PackageItem(name='多机位副机 + 图传', qty=1, model='按需', brand='—'),
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
    risks.append('假电池、HDMI 线、SD 卡、插排等耗材未计入主清单，落地时需预留 5-10% 机动预算')

    steps = [
        '第1步：确认场地尺寸、层高与窗户位置，完成遮光与基础动线规划。',
        '第2步：按主机位、商品区、背景区划分功能分区，固定三脚架与灯架点位。',
        f'第3步：安装 {mid_light.brand} {mid_light.model} 主灯与 {mid_soft.model} 柔光箱，完成三点布光并微调光比。',
        f'第4步：架设 {mid_cam.brand} {mid_cam.model} + {mid_capture.model} 采集链路，校准白平衡、曝光与对焦距离。',
        f'第5步：接入 {mid_audio.brand} 声卡与监听，布置背景层次与商品展示位，完成 10 分钟试播验收。',
    ]

    host_note = f'{brief.host_count} 位主播' if brief.host_count else '单主播'
    movement_note = {
        'sit': '以坐姿为主，机位可更近',
        'occasional': '偶尔站起，预留小幅活动空间',
        'frequent': '经常走动，需更大景别与跟拍余量',
        'wide': '大范围移动，建议增加辅助机位与更大布光覆盖',
    }.get(brief.host_movement, '默认站姿半身构图')
    scale = _ROOM_SCALE.get(brief.room_size, _ROOM_SCALE['medium'])
    layout_scale = (
        f'建议面积 {scale["area"]}；净高 {scale["ceiling"]}；'
        f'供电 {scale["power"]}；机位配置 {scale["hosts"]}'
    )

    return PlanDraft(
        meta={
            'brand': brief.brand,
            'industry': brief.industry,
            'room_size': brief.room_size,
            'budget_total': brief.budget_total,
            'area_band': brief.area_band or scale['area'],
            'layout_scale': layout_scale,
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
                LayoutZone(
                    name='主播区',
                    notes=(
                        f'{host_note}；{movement_note}；{layout_scale}；'
                        '旁设换鞋凳与亚克力旋转鞋台，方便上脚与 360° 展示'
                    )
                    if brief.industry == 'shoes'
                    else f'{host_note}；{movement_note}；{layout_scale}',
                ),
                LayoutZone(
                    name='商品展示区',
                    notes=(
                        f'双层鞋墙陈列「{brief.product_main or "鞋款"}」，'
                        '镜面地台反射鞋底纹路，鞋盒堆叠强化仓播真实感'
                    )
                    if brief.industry == 'shoes'
                    else f'围绕主营「{brief.product_main or "商品"}」布置近景展示位，预留特写台面',
                ),
                LayoutZone(
                    name='背景区',
                    notes=(
                        '深灰工业风模块墙 + 橙色品牌点缀灯带，'
                        '避免高饱和抢鞋款配色；保留尺码对照表角标区'
                    )
                    if brief.industry == 'shoes'
                    else '建立 2–3 层视觉层次，避免单调平面；控制 logo 与杂乱电线入画',
                ),
            ],
            lighting_plan=(
                f'三点布光：{mid_light.brand} {mid_light.model} 主灯 45° 侧上压高光，'
                f'侧逆光勾勒鞋面轮廓与中底层次；色温统一 {color_temp}，'
                '镜面地台注意控反射（主灯加格栅）。'
            )
            if brief.industry == 'shoes'
            else (
                f'三点布光：{mid_light.brand} {mid_light.model} 主灯 45°，'
                f'{mid_soft.model} 柔光箱 + 副灯补光，发丝灯勾边；'
                f'色温统一 {color_temp} 左右，全链路手动白平衡。'
            ),
            camera_plan=(
                f'主机位 {mid_cam.brand} {mid_cam.model} 正面半身讲款；'
                '细节机位对准鞋面材质与外底纹路；下移机位拍上脚效果；'
                '后侧机位交代鞋墙与动线纵深；经 '
                f'{mid_capture.brand} {mid_capture.model} 采集推流。'
            )
            if brief.industry == 'shoes'
            else (
                f'主机位 {mid_cam.brand} {mid_cam.model} 正面半身；'
                f'副机位左侧 45° 补商品特写；预留后侧纵深位；'
                f'经 {mid_capture.brand} {mid_capture.model} 采集推流。'
            ),
            background_plan=(
                '鞋墙 + 鞋盒堆叠建立真实仓播层次，控制 logo 与杂乱电线入画。'
            )
            if brief.industry == 'shoes'
            else '背景与品牌关键词对齐，控制 logo 与杂乱元素入画；可拆卸材料优先。',
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
            product_category=(
                f'{brief.product_main or "运动鞋"}｜鞋墙陈列｜上脚试穿台'
                if brief.industry == 'shoes'
                else (brief.product_main or industry_label(brief.industry))
            ),
            camera_angles=['front', 'left', 'rear'],
            forbidden=['文字水印', '品牌logo', '杂乱电线入画'],
        ),
        rental_channels=_RENTAL_CHANNELS,
        vertical_notes=_vertical_notes(brief.industry, brief.product_main),
        must_buy_list=must_buy_list,
    )
