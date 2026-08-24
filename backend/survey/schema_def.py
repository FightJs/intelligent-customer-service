"""调研表 v1 schema 定义（单一数据源 - UI 元数据 + 条件分支）。

这里是调研表《直播间视觉向量化优化 - 用户调研表》的完整 Python 表示。
前端 TS 通过 codegen（export.py → gen-schema.ts）从本文件生成，保证前后端一致。

字段严格对应团队确认的 2026 最终问答模板。内部运营字段不进入客户问卷。
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────────────────────────
# 元数据类型
# ──────────────────────────────────────────────────────────────

FieldType = Literal[
    'text',
    'choice-single',
    'choice-multi',
    'dimension',
    'image',
    'table',
]


class OptionDef(BaseModel):
    model_config = ConfigDict(extra='forbid')
    value: str
    label: str


class VisibleIf(BaseModel):
    """条件分支：仅当指定字段等于（或不等于）某值时，本字段才可见。"""
    model_config = ConfigDict(extra='forbid')
    field_id: str           # 依赖的字段（同 section 内）
    op: Literal['eq', 'ne'] = 'eq'
    value: str              # 比较值


class TableColumn(BaseModel):
    """table 字段的列定义。"""
    model_config = ConfigDict(extra='forbid')
    id: str
    label: str
    placeholder: str = ''


class FieldDef(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    label: str
    question: str
    type: FieldType
    required: bool = False
    skippable: bool = False
    ask_in_full: bool = True
    help_text: str = ''
    options: list[OptionDef] | None = None          # choice-* 用
    dims: list[str] | None = None                    # dimension 用：['宽','深','高']
    unit: str = ''                                   # dimension 用：'m' / 'cm'
    placeholder: str = ''                            # text 用
    columns: list[TableColumn] | None = None         # table 用：列定义
    visible_if: VisibleIf | None = None              # 条件分支


class SectionDef(BaseModel):
    model_config = ConfigDict(extra='forbid')
    id: str
    title: str               # '一、客户基础信息'
    hint: str = ''           # 章节顶部提示（调研表里的"重要：..."说明格）
    order: int
    skippable: bool = False
    visible_if: VisibleIf | None = None
    fields: list[FieldDef]


# ──────────────────────────────────────────────────────────────
# 选项常量（被多个字段复用，集中定义减少重复）
# ──────────────────────────────────────────────────────────────

QUICK_REQUIRED_FIELD_IDS = [
    'customer.brand',
    'industry.category',
    'industry.subcategory',
    'industry.price_band',
    'industry.live_type',
    'status.has_room',
    'venue.area',
    'budget.total',
    'product.main',
    'product.keywords',
    'goal.core',
    'goal.deadline',
]



_YES_NO = [OptionDef(value='yes', label='是'), OptionDef(value='no', label='否')]

_INDUSTRY_CATEGORIES = [
    OptionDef(value='women', label='女装'),
    OptionDef(value='men', label='男装'),
    OptionDef(value='beauty', label='美妆'),
    OptionDef(value='food', label='食品'),
    OptionDef(value='jewelry', label='珠宝'),
    OptionDef(value='home', label='家居'),
    OptionDef(value='digital', label='数码'),
    OptionDef(value='baby', label='母婴'),
    OptionDef(value='other', label='其他'),
]

_PRICE_BAND = [
    OptionDef(value='low', label='低客单（<100元）'),
    OptionDef(value='mid', label='中客单（100-500元）'),
    OptionDef(value='high', label='高客单（500-2000元）'),
    OptionDef(value='ultra', label='超高客单（>2000元）'),
]

_POSITIONING = [
    OptionDef(value='mass', label='平价大众'),
    OptionDef(value='value', label='性价比'),
    OptionDef(value='mid-high', label='中高端'),
    OptionDef(value='luxury', label='轻奢/高端'),
    OptionDef(value='premium', label='奢侈品'),
]

_AGE_GROUP = [
    OptionDef(value='18-25', label='18-25岁'),
    OptionDef(value='25-35', label='25-35岁'),
    OptionDef(value='35-45', label='35-45岁'),
    OptionDef(value='45+', label='45岁以上'),
]

_GENDER = [
    OptionDef(value='female', label='女性为主'),
    OptionDef(value='male', label='男性为主'),
    OptionDef(value='balanced', label='男女均衡'),
]

_LIVE_TYPE = [
    OptionDef(value='influencer', label='达人带货'),
    OptionDef(value='brand', label='品牌自播'),
    OptionDef(value='factory', label='工厂店播'),
    OptionDef(value='ip', label='个人IP'),
    OptionDef(value='other', label='其他'),
]

_CUSTOMER_SOURCE = [
    OptionDef(value='douyin', label='抖音直播'),
    OptionDef(value='ads', label='信息流广告'),
    OptionDef(value='referral', label='朋友推荐'),
    OptionDef(value='other', label='其他'),
]

_BROADCAST_DURATION = [
    OptionDef(value='none', label='未开播'),
    OptionDef(value='1m', label='1个月内'),
    OptionDef(value='1-3m', label='1-3个月'),
    OptionDef(value='3-6m', label='3-6个月'),
    OptionDef(value='6m+', label='6个月以上'),
]

_VIEWERS = [
    OptionDef(value='<500', label='<500人'),
    OptionDef(value='500-2k', label='500-2000人'),
    OptionDef(value='2k-10k', label='2000-1万人'),
    OptionDef(value='10k+', label='1万人以上'),
]

_GMV = [
    OptionDef(value='<5k', label='<5000元'),
    OptionDef(value='5k-2w', label='5000-2万'),
    OptionDef(value='2w-10w', label='2万-10万'),
    OptionDef(value='10w+', label='10万以上'),
]

_SATISFACTION = [
    OptionDef(value='very_bad', label='很不满意'),
    OptionDef(value='bad', label='不太满意'),
    OptionDef(value='neutral', label='一般'),
    OptionDef(value='good', label='比较满意'),
    OptionDef(value='very_good', label='非常满意'),
]

_PAIN_POINTS = [
    OptionDef(value='traffic', label='流量少'),
    OptionDef(value='retention', label='留不住人'),
    OptionDef(value='conversion', label='转化率低'),
    OptionDef(value='visual', label='画面不好看'),
    OptionDef(value='equipment', label='设备不会调'),
    OptionDef(value='other', label='其他'),
]

_AREA = [
    OptionDef(value='<10', label='<10㎡'),
    OptionDef(value='10-20', label='10-20㎡'),
    OptionDef(value='20-30', label='20-30㎡'),
    OptionDef(value='30-50', label='30-50㎡'),
    OptionDef(value='50+', label='50㎡以上'),
]

_WINDOW = [
    OptionDef(value='none', label='无窗户'),
    OptionDef(value='coverable', label='有窗户但可遮挡'),
    OptionDef(value='uncoverable', label='有窗户无法遮挡'),
]

_WINDOW_POS = [
    OptionDef(value='behind', label='主播背后'),
    OptionDef(value='front', label='主播正面'),
    OptionDef(value='left', label='主播左侧'),
    OptionDef(value='right', label='主播右侧'),
]

_RENOVATION = [
    OptionDef(value='major', label='可以大改'),
    OptionDef(value='minor', label='可以小改'),
    OptionDef(value='none', label='不能改动'),
    OptionDef(value='unsure', label='不确定'),
]

_TOTAL_BUDGET = [
    OptionDef(value='<1w', label='1万以下'),
    OptionDef(value='1-3w', label='1-3万'),
    OptionDef(value='3-5w', label='3-5万'),
    OptionDef(value='5-10w', label='5-10万'),
    OptionDef(value='10-20w', label='10-20万'),
    OptionDef(value='20w+', label='20万以上'),
]

_EQUIP_BUDGET = [
    OptionDef(value='<5k', label='5千以下'),
    OptionDef(value='5k-1w', label='5千-1万'),
    OptionDef(value='1-2w', label='1-2万'),
    OptionDef(value='2-5w', label='2-5万'),
    OptionDef(value='5w+', label='5万以上'),
]

_DECOR_BUDGET = [
    OptionDef(value='<5k', label='5千以下'),
    OptionDef(value='5k-1w', label='5千-1万'),
    OptionDef(value='1-3w', label='1-3万'),
    OptionDef(value='3-5w', label='3-5万'),
    OptionDef(value='5w+', label='5万以上'),
]

_BUDGET_FLEX = [
    OptionDef(value='tight', label='很紧张，不能超'),
    OptionDef(value='some', label='有10%左右浮动空间'),
    OptionDef(value='flexible', label='比较灵活，效果优先'),
]

_PRODUCT_SIZE = [
    OptionDef(value='tiny', label='很小（首饰类）'),
    OptionDef(value='small', label='小（美妆类）'),
    OptionDef(value='medium', label='中（服装类）'),
    OptionDef(value='large', label='大（家居类）'),
]

_HOST_COUNT = [
    OptionDef(value='1', label='1人'),
    OptionDef(value='2', label='2人'),
    OptionDef(value='3+', label='3人及以上'),
]

_MOVEMENT = [
    OptionDef(value='sit', label='基本坐着'),
    OptionDef(value='occasional', label='偶尔站起'),
    OptionDef(value='frequent', label='经常走动'),
    OptionDef(value='wide', label='大范围移动'),
]

_CORE_NEED = [
    OptionDef(value='new', label='全新搭建直播间'),
    OptionDef(value='optimize', label='优化现有直播间'),
    OptionDef(value='tune', label='只调设备参数'),
    OptionDef(value='decor', label='只做装修设计'),
    OptionDef(value='full', label='全套方案'),
]

_FOCUS_EFFECT = [
    OptionDef(value='premium-look', label='画面高级感'),
    OptionDef(value='host-look', label='主播好看'),
    OptionDef(value='product-quality', label='商品质感'),
    OptionDef(value='pro-lighting', label='灯光专业'),
    OptionDef(value='value', label='性价比高'),
    OptionDef(value='other', label='其他'),
]

_NEED_3D = [OptionDef(value='yes', label='需要'), OptionDef(value='no', label='不需要')]

_DEADLINE = [
    OptionDef(value='3d', label='3天内'),
    OptionDef(value='1w', label='一周内'),
    OptionDef(value='2w', label='两周内'),
    OptionDef(value='flexible', label='不着急'),
]

_BENCHMARK_PLATFORM = [
    OptionDef(value='douyin', label='抖音'),
    OptionDef(value='taobao', label='淘宝直播'),
    OptionDef(value='kuaishou', label='快手'),
    OptionDef(value='wechat', label='视频号'),
    OptionDef(value='xiaohongshu', label='小红书'),
    OptionDef(value='other', label='其他'),
]

_BENCHMARK_LIKES = [
    OptionDef(value='overall', label='整体风格'),
    OptionDef(value='background', label='背景装修'),
    OptionDef(value='lighting', label='灯光效果'),
    OptionDef(value='composition', label='机位构图'),
    OptionDef(value='display', label='商品展示'),
    OptionDef(value='color', label='色彩搭配'),
    OptionDef(value='other', label='其他'),
]

_REFERENCE_MODE = [
    OptionDef(value='optimize-primary', label='以主对标为基础优化'),
    OptionDef(value='combine', label='综合多个对标优点'),
    OptionDef(value='elements-only', label='只参考元素，不整体模仿'),
]

_EXACT_COPY = [
    OptionDef(value='yes', label='是，尽量1:1还原'),
    OptionDef(value='no', label='否，参考风格但要有自己特色'),
]

# 设备明细表列定义（第八节）
_EQUIPMENT_COLUMNS = [
    TableColumn(id='type', label='设备类型', placeholder='相机/镜头/主灯等'),
    TableColumn(id='model', label='品牌型号', placeholder='例：Sony A7M4'),
    TableColumn(id='qty', label='数量', placeholder='数量'),
]


# ──────────────────────────────────────────────────────────────
# 十章节定义（对照调研表逐章录入）
# ──────────────────────────────────────────────────────────────

SECTIONS: list[SectionDef] = [


    # ── 一、客户基础信息 ──
    SectionDef(
        id='customer', title='一、基础信息采集', order=1,
        hint='核心必填：用于方案归档与后续对接。',
        fields=[
            FieldDef(
                id='brand', label='品牌/公司名称', question='请问您的品牌或公司名称是什么？',
                type='text', required=True, placeholder='如：云裳',
                help_text='填写说明：用于方案标题与正式归档，是生成专属方案的核心标识。',
            ),
            FieldDef(
                id='contact', label='姓名', question='方便留下您的姓名和联系电话吗？',
                type='text', required=True, placeholder='联系人姓名',
                help_text='填写说明：方便我们后续对接方案细节，确保能第一时间给到您完整的方案内容。',
            ),
            FieldDef(
                id='phone', label='联系电话', question='联系电话还没有记录，方便再补充一下吗？',
                type='text', required=True, placeholder='138****',
                help_text='填写说明：方便我们后续对接方案细节，确保能第一时间给到您完整的方案内容。',
            ),
            FieldDef(
                id='source', label='了解渠道', question='您是通过哪个渠道了解到我们的？',
                type='choice-single', required=True, options=_CUSTOMER_SOURCE,
                help_text='填写说明：用于我们统计客户来源，优化服务渠道，也能帮您匹配对应渠道的专属服务资源。',
            ),
            FieldDef(
                id='wechat', label='微信号', question='方便留下您的微信号吗？',
                type='text', skippable=True, placeholder='选填，便于发送效果图和设备清单',
                help_text='填写说明：方便后续微信端给您发送方案效果图、设备清单等详细资料。',
            ),
            FieldDef(
                id='city', label='所在城市', question='请问您所在的城市是哪里？',
                type='text', skippable=True, placeholder='选填，如需线下服务可匹配资源',
                help_text='填写说明：如果您有线下服务需求，我们可以帮您匹配对应城市的落地资源。',
            ),
        ],
    ),


    # ── 二、行业与品类信息 ──
    SectionDef(
        id='industry', title='二、行业与品类信息', order=2,
        hint='核心信息：用于匹配视觉方向。按当前业务要求，大类和细分品类允许跳过。',
        fields=[
            FieldDef(
                id='category', label='行业大类', question='您的直播间主营什么行业大类？',
                type='choice-single', skippable=True, options=_INDUSTRY_CATEGORIES,
                help_text='填写说明：不同行业的直播间视觉逻辑、商品展示方式差异极大，明确行业能帮您匹配最贴合的方案模板。',
            ),
            FieldDef(
                id='subcategory', label='细分品类', question='更具体的细分品类是什么？',
                type='text', skippable=True,
                placeholder='例：高端香云纱女装、黄金珠宝、进口零食',
                help_text='填写示例：高端香云纱女装、黄金珠宝、进口零食，越具体，生成的方案越精准。',
            ),
            FieldDef(
                id='price_band', label='商品价格带', question='您的商品价格带大致是多少？',
                type='choice-single', required=True, options=_PRICE_BAND,
                help_text='填写说明：价格带直接决定直播间的档次定位、视觉风格方向，是方案设计的核心参考。',
            ),
            FieldDef(
                id='price_range_raw', label='用户原始商品价格范围',
                question='（系统自动保留用户给出的具体价格范围）',
                type='text', ask_in_full=False,
                help_text='保留用户原话，避免区间归类后丢失精度。',
            ),
            FieldDef(
                id='positioning', label='品牌定位', question='您的品牌定位属于哪一类？',
                type='choice-single', required=True, options=_POSITIONING,
                help_text='填写说明：品牌定位决定了直播间的视觉基调，避免方案风格和品牌调性脱节。',
            ),
            FieldDef(
                id='target_age', label='目标客群年龄', question='核心目标客群年龄主要集中在哪个区间？',
                type='choice-single', required=True, options=_AGE_GROUP,
                help_text='填写说明：不同年龄层的色彩偏好、视觉审美差异很大，能帮您优化直播间的视觉吸引力。',
            ),
            FieldDef(
                id='target_gender', label='目标客群性别', question='目标客群的性别偏向是怎样的？',
                type='choice-single', required=True, options=_GENDER,
                help_text='填写说明：针对性别优化视觉风格，能有效提升目标用户的停留意愿。',
            ),
            FieldDef(
                id='live_type', label='直播间类型', question='您的直播间属于哪种类型？',
                type='choice-single', required=True, options=_LIVE_TYPE,
                help_text='填写说明：不同类型的直播间，视觉设计、设备选型的标准完全不同，明确类型能避免方案跑偏。',
            ),
        ],
    ),


    # ── 三、直播间现状 ──（条件：has_room=yes 才填其余）
    SectionDef(
        id='status', title='三、直播间现状', order=3,
        hint='选填：已有直播间时补充；没有直播间可直接跳过本模块。',
        skippable=True,
        fields=[
            FieldDef(
                id='has_room', label='是否已有直播间', question='您目前已经有正在运营的直播间了吗？',
                type='choice-single', options=_YES_NO,
                help_text='填写说明：用于判断是否继续了解现有直播间情况；没有直播间时将直接进入后续模块。',
            ),
            # 以下字段仅在 has_room=yes 时可见
            FieldDef(
                id='room_photo', label='直播间照片/风格参考图',
                question='方便上传当前直播间照片，或希望对比的直播间样式参考图吗？',
                type='image', skippable=True,
                help_text='填写说明：可直接用于方案优化校准，让生成的方案更贴合您的实际情况，无需文字描述，拍照即可。',
                visible_if=VisibleIf(field_id='has_room', value='yes'),
            ),
            FieldDef(
                id='duration', label='开播时长', question='目前大约开播多久了？',
                type='choice-single', skippable=True, options=_BROADCAST_DURATION,
                help_text='填写说明：了解直播间运营阶段，辅助判断优化侧重点。',
                visible_if=VisibleIf(field_id='has_room', value='yes'),
            ),
            FieldDef(
                id='viewers', label='当前场均观看', question='当前直播间的场均观看人数大概是多少？',
                type='choice-single', skippable=True, options=_VIEWERS,
                help_text='填写说明：帮您判断当前流量层级，针对性优化视觉引流方案。',
                visible_if=VisibleIf(field_id='has_room', value='yes'),
            ),
            FieldDef(
                id='gmv', label='当前场均GMV', question='当前直播间的场均GMV大概是多少？',
                type='choice-single', skippable=True, options=_GMV,
                help_text='填写说明：结合经营数据，匹配适配的视觉投入方案。',
                visible_if=VisibleIf(field_id='has_room', value='yes'),
            ),
            FieldDef(
                id='satisfaction', label='对现状是否满意', question='您对当前直播间的整体现状满意吗？',
                type='choice-single', skippable=True, options=_SATISFACTION,
                help_text='填写说明：了解主观感受，找准优化方向。',
                visible_if=VisibleIf(field_id='has_room', value='yes'),
            ),
            FieldDef(
                id='pain_points', label='主要痛点', question='当前直播间最核心的痛点有哪些？',
                type='choice-multi', skippable=True, options=_PAIN_POINTS,
                help_text='填写说明：明确痛点后，我们的方案会优先针对您的问题做优化，精准解决您的需求。',
                visible_if=VisibleIf(field_id='has_room', value='yes'),
            ),
        ],
    ),


    # ── 四、场地条件信息 ──
    SectionDef(
        id='venue', title='四、场地条件信息', order=4,
        hint='核心必填：场地条件直接决定设备选型与装修方案。',
        fields=[
            FieldDef(
                id='area', label='直播间面积', question='您的直播间场地面积大概是多少？',
                type='choice-single', required=True, options=_AREA,
                help_text='填写说明：面积是直播间布局、设备选型的核心基础，能帮您规划最合理的空间利用方案。',
            ),
            FieldDef(
                id='size', label='具体尺寸（宽×深×高）', question='方便提供场地的宽、深、高吗？',
                type='dimension', skippable=True, dims=['宽', '深', '高'], unit='m',
                help_text='填写示例：宽__m × 深__m × 高__m，尺寸越精准，方案的落地性越强；不方便测量可直接拍照上传。',
            ),
            FieldDef(
                id='window', label='窗户情况', question='场地的窗户情况是怎样的？',
                type='choice-single', required=True, options=_WINDOW,
                help_text='填写说明：窗户情况直接影响灯光方案的设计，避免自然光干扰直播画面效果。',
            ),
            FieldDef(
                id='window_pos', label='窗户位置', question='如果有窗户，窗户在主播的哪个位置？',
                type='choice-single', skippable=True, options=_WINDOW_POS,
                help_text='填写说明：用于灯光布光方案设计，规避逆光、杂光问题。',
                visible_if=VisibleIf(field_id='window', op='ne', value='none'),
            ),
            FieldDef(
                id='renovation', label='是否允许装修', question='您的场地允许装修改动吗？',
                type='choice-single', required=True, options=_RENOVATION,
                help_text='填写说明：明确装修权限，能帮您制定完全贴合场地情况的方案，避免方案无法落地。',
            ),
            FieldDef(
                id='venue_photo', label='场地多角度照片', question='方便上传场地的多角度照片吗？',
                type='image', skippable=True,
                help_text='填写说明：能让我们更直观地了解场地情况，避免方案和实际场地不符，直接拍照上传即可，不用手动描述细节。',
            ),
        ],
    ),


    # ── 五、预算范围信息 ──
    SectionDef(
        id='budget', title='五、预算范围信息', order=5,
        hint='核心必填：用于控制方案成本与设备选型。',
        fields=[
            FieldDef(
                id='total', label='总预算范围', question='本次直播间搭建或优化的总预算范围是多少？',
                type='choice-single', required=True, options=_TOTAL_BUDGET,
                help_text='填写说明：预算是方案设计的核心边界，能帮您制定性价比最高的方案，避免超支。',
            ),
            FieldDef(
                id='equipment', label='设备采购预算', question='总预算中，设备采购大概安排多少？',
                type='choice-single', required=True, options=_EQUIP_BUDGET,
                help_text='填写说明：用于相机、灯光等核心设备的选型匹配，确保设备预算和总预算匹配。',
            ),
            FieldDef(
                id='decor', label='装修装饰预算', question='总预算中，装修装饰大概安排多少？',
                type='choice-single', required=True, options=_DECOR_BUDGET,
                help_text='填写说明：用于背景墙、装饰等装修内容的规划，确保装修方案在预算范围内。',
            ),
            FieldDef(
                id='flex', label='预算弹性', question='您的预算弹性如何？',
                type='choice-single', skippable=True, options=_BUDGET_FLEX,
                help_text='填写说明：便于我们在方案中预留调整空间。',
            ),
            FieldDef(
                id='has_existing', label='是否已有部分设备', question='您目前已经有部分直播设备了吗？',
                type='choice-single', required=True, options=_YES_NO,
                help_text='填写说明：有设备的话我们会基于现有设备做优化，不用重复采购，帮您节省成本。',
            ),
        ],
    ),


    # ── 六、商品与品牌视觉信息 ──
    SectionDef(
        id='product', title='六、商品与品牌视觉信息', order=6,
        hint='核心必填：商品与品牌信息是场景设计的依据。',
        fields=[
            FieldDef(
                id='main', label='主营商品类型', question='直播间的主营商品类型是什么？',
                type='text', required=True, placeholder='例：连衣裙、口红、翡翠手镯',
                help_text='填写示例：连衣裙、口红、翡翠手镯，越具体越好。',
            ),
            FieldDef(
                id='size_cat', label='商品尺寸', question='您的商品尺寸属于哪一类？',
                type='choice-single', required=True, options=_PRODUCT_SIZE,
                help_text='填写说明：商品尺寸直接决定了展示方式、机位构图，能帮您优化商品的呈现效果。',
            ),
            FieldDef(
                id='keywords', label='品牌风格关键词', question='可以说3到5个品牌风格关键词吗？',
                type='text', required=True,
                placeholder='例：国风、高端、雅致、轻奢、简约',
                help_text='填写示例：国风、高端、雅致、轻奢、简约，越具体，方案风格越贴合。',
            ),
            FieldDef(
                id='style_ref', label='喜欢的直播间风格参考',
                question='有喜欢的直播间风格参考吗？可以描述账号或直接上传截图。',
                type='text', skippable=True, placeholder='可填写参考直播间账号或名称',
                help_text='填写说明：可提供参考直播间账号或截图图片，能让我们更精准地匹配您的审美偏好。',
            ),
            FieldDef(
                id='style_ref_image', label='风格参考截图', question='方便上传喜欢的直播间截图吗？',
                type='image', skippable=True,
                help_text='填写说明：可提供参考直播间账号或截图图片，能让我们更精准地匹配您的审美偏好。',
            ),
            FieldDef(
                id='dislike_style', label='明确不喜欢的风格', question='有没有您明确不喜欢的风格？',
                type='text', skippable=True, placeholder='明确需要避开的方向',
                help_text='填写说明：明确避开的方向，避免生成的方案不符合您的审美。',
            ),
            FieldDef(
                id='brand_assets', label='品牌Logo/VI与商品样品图',
                question='方便上传品牌Logo、VI或商品样品图吗？',
                type='image', skippable=True,
                help_text='填写说明：可将品牌元素融入背景设计，同时针对商品做专属的展示优化，让方案更贴合品牌，直接上传图片即可。',
            ),
        ],
    ),


    # ── 七、对标直播间参考 ──
    SectionDef(
        id='benchmark', title='七、对标直播间参考', order=7,
        hint='选填：没有对标直播间可直接跳过本模块。',
        skippable=True,
        fields=[
            FieldDef(
                id='has_benchmark', label='是否有对标直播间', question='您有想要对标的直播间吗？',
                type='choice-single', options=_YES_NO,
                help_text='填写说明：用于判断是否继续采集对标信息；没有对标直播间时将直接进入后续模块。',
            ),
            FieldDef(
                id='account_name', label='主对标账号/名称',
                question='请发一下主对标直播间的账号、链接或截图。',
                type='text', skippable=True,
                help_text='填写说明：对标直播间是视觉风格匹配的核心参考，信息越完整，生成的方案越精准。',
                visible_if=VisibleIf(field_id='has_benchmark', value='yes'),
            ),
            FieldDef(
                id='platform', label='主对标平台', question='这个主对标直播间在哪个平台？',
                type='choice-single', skippable=True, options=_BENCHMARK_PLATFORM,
                help_text='填写说明：不同平台的直播间风格差异很大，明确平台能避免方案和平台生态脱节。',
                visible_if=VisibleIf(field_id='has_benchmark', value='yes'),
            ),
            FieldDef(
                id='likes', label='喜欢的方面', question='您最喜欢这个直播间的哪些方面？',
                type='choice-multi', skippable=True, options=_BENCHMARK_LIKES,
                help_text='填写说明：明确喜欢的点，我们会把这些优势融入到您的方案中，同时避免照搬短板。',
                visible_if=VisibleIf(field_id='has_benchmark', value='yes'),
            ),
            FieldDef(
                id='screenshot', label='对标截图/图片', question='方便上传对标直播间的截图吗？',
                type='image', skippable=True,
                help_text='填写说明：可直接用于向量化分析，提取核心视觉特征，让方案更贴合您的对标需求，截图拍照上传即可。',
                visible_if=VisibleIf(field_id='has_benchmark', value='yes'),
            ),
            FieldDef(
                id='reference_link', label='对标直播间链接',
                question='有对标直播间的链接可以补充吗？',
                type='text', skippable=True,
                placeholder='可粘贴直播间或作品链接',
                help_text='填写说明：可直接用于向量化分析，提取核心视觉特征，让方案更贴合您的对标需求。',
                visible_if=VisibleIf(field_id='has_benchmark', value='yes'),
            ),
            FieldDef(
                id='reference_mode', label='参考方式', question='您希望以哪种方式参考对标直播间？',
                type='choice-single', skippable=True, options=_REFERENCE_MODE,
                help_text='填写说明：确定借鉴逻辑，控制方案原创程度。',
                visible_if=VisibleIf(field_id='has_benchmark', value='yes'),
            ),
            FieldDef(
                id='exact_copy', label='是否完全复刻', question='您需要尽量1:1复刻对标直播间吗？',
                type='choice-single', skippable=True, options=_EXACT_COPY,
                help_text='填写说明：区分复刻还是借鉴，把控方案输出方向。',
                visible_if=VisibleIf(field_id='has_benchmark', value='yes'),
            ),
        ],
    ),


    # ── 八、主播信息 ──
    SectionDef(
        id='host', title='八、主播信息', order=8,
        hint='选填：没有特殊主播适配需求可直接跳过本模块。',
        skippable=True,
        fields=[
            FieldDef(
                id='count', label='主播人数', question='直播间通常有几位主播？',
                type='choice-single', options=_HOST_COUNT,
                help_text='填写说明：主播人数会影响机位布局、构图设计，确保直播画面能适配所有主播。',
            ),
            FieldDef(
                id='movement', label='主播活动状态', question='直播时主播通常是坐着、站起还是会走动？',
                type='choice-single', options=_MOVEMENT,
                help_text='填写说明：影响镜头选型、空间布局，确保主播活动时画面始终稳定清晰。',
            ),
            FieldDef(
                id='profile', label='主播身高与体型补充', question='主播的身高、体型等信息方便补充吗？',
                type='text', skippable=True,
                placeholder='选填，用于机位高度和构图适配',
                help_text='填写说明：帮您优化机位高度、构图角度，让主播在画面里呈现更好的状态。',
            ),
        ],
    ),


    # ── 九、现有设备情况 ──（仅已有设备时显示）
    SectionDef(
        id='equipment', title='九、现有设备情况', order=9,
        hint='选填：认识型号可文字填写；不认识型号可直接拍摄设备照片。',
        skippable=True,
        visible_if=VisibleIf(field_id='budget.has_existing', value='yes'),
        fields=[
            FieldDef(
                id='inventory', label='现有设备文字明细',
                question='可以描述现有设备的类型、型号和数量；不清楚型号也可以直接拍照上传。',
                type='table', skippable=True, columns=_EQUIPMENT_COLUMNS,
                help_text='填写指引：认识设备型号就填写品牌型号和数量；不认识型号无需猜测，可以直接拍摄上传设备照片，后端设备人员会帮您核对检测。',
            ),
            FieldDef(
                id='equipment_photo', label='现有设备照片',
                question='方便再拍摄并上传现有设备照片吗？',
                type='image', skippable=True,
                help_text='填写指引：不认识设备型号无需猜测，可以直接拍摄上传设备照片，后端设备人员会帮您核对检测。',
            ),
        ],
    ),


    # ── 十、核心需求与目标 ──
    SectionDef(
        id='goal', title='十、核心需求与目标', order=10,
        hint='核心必填：用于明确服务范围与交付标准。',
        fields=[
            FieldDef(
                id='core', label='核心需求', question='本次最核心的需求是什么？',
                type='choice-single', required=True, options=_CORE_NEED,
                help_text='填写说明：明确服务范围，确保我们给到的方案完全匹配您的需求，不做无效内容。',
            ),
            FieldDef(
                id='focus', label='最看重的效果', question='您最看重直播间的哪些效果？',
                type='choice-multi', required=True, options=_FOCUS_EFFECT,
                help_text='填写说明：明确核心优先级，我们会优先保障您最看重的效果落地。',
            ),
            FieldDef(
                id='need_3d', label='是否需要3D效果图', question='您需要提供3D效果图吗？',
                type='choice-single', required=True, options=_NEED_3D,
                help_text='填写说明：影响最终的交付内容，需要的话我们会同步生成多视角3D效果图。',
            ),
            FieldDef(
                id='deadline', label='期望交付时间', question='您期望什么时候完成交付？',
                type='choice-single', required=True, options=_DEADLINE,
                help_text='填写说明：便于项目排期，按时输出方案。',
            ),
            FieldDef(
                id='other', label='其他特殊要求',
                question='还有其他特殊要求或参考图需要补充吗？可以文字说明或直接上传。',
                type='text', skippable=True, placeholder='选填，任何特殊需求都可以写',
                help_text='填写说明：任何特殊需求都可以在这里说明，也可以直接上传参考图片，我们会在方案里优先满足。',
            ),
            FieldDef(
                id='other_reference', label='特殊要求补充参考图',
                question='需要上传补充参考图吗？', type='image', skippable=True,
                help_text='填写说明：任何特殊需求都可以在这里说明，也可以直接上传参考图片，我们会在方案里优先满足。',
            ),
        ],
    ),
]


# 章节顺序（用于流程推进）
SECTION_ORDER: list[str] = [s.id for s in SECTIONS]

# 快速索引
SECTION_BY_ID: dict[str, SectionDef] = {s.id: s for s in SECTIONS}
FIELD_BY_ID: dict[str, FieldDef] = {
    f.id: f for s in SECTIONS for f in s.fields
}

# 调研表附：客服填写指南（作为 agent system prompt 的 SOP）
AGENT_GUIDE = """\
客服填写原则：
- 角色只负责收集需求，不展开分析、不输出搭建方案、不做设备推荐
- 先用一个短句回应用户情绪或确认已记录，再提出当前唯一问题
- 问题按模板顺序推进；只有标记可跳过的题目或模块才能跳过
- 用户给出具体数字区间时保留边界含义，不得擅自换成相邻档位
- 不确定的信息必须追问确认，不能猜测
- 图片只在对应图片题或设备题出现时邀请，拒绝或跳过后不再追问

常见问题引导：
- 客户询问方案：简短说明“先把需求收集完整，后续会根据记录形成方案”，然后回到当前问题
- 客户预算不明确：给出模板中的预算档位让客户选择，不替客户决定
- 客户不知道设备型号：允许文字描述，也可直接拍摄上传设备照片
"""
