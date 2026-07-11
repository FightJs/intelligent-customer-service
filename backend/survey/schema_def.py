"""调研表 v1 schema 定义（单一数据源 - UI 元数据 + 条件分支）。

这里是调研表《直播间视觉向量化优化 - 用户调研表》的完整 Python 表示。
前端 TS 通过 codegen（export.py → gen-schema.ts）从本文件生成，保证前后端一致。

字段对照调研表十章节：
  一、客户基础信息      customer    7 字段
  二、行业与品类信息    industry    7 字段
  三、直播间现状        status      8 字段（条件：是否有直播间）
  四、场地条件信息      venue      10 字段
  五、预算范围信息      budget      5 字段
  六、商品与品牌视觉    product     9 字段
  七、主播信息          host        7 字段
  八、现有设备情况      equipment   8 字段（table 类型，条件：是否已有设备）
  九、需求与目标        goal        6 字段
  十、客服备注          notes       5 字段
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
    type: FieldType
    required: bool = False
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
    fields: list[FieldDef]


# ──────────────────────────────────────────────────────────────
# 选项常量（被多个字段复用，集中定义减少重复）
# ──────────────────────────────────────────────────────────────

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

_ROOM_SHAPE = [
    OptionDef(value='rect', label='长方形'),
    OptionDef(value='square', label='正方形'),
    OptionDef(value='l-shape', label='L型'),
    OptionDef(value='other', label='其他'),
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

_WALL_COLOR = [
    OptionDef(value='white', label='白色'),
    OptionDef(value='gray', label='灰色'),
    OptionDef(value='beige', label='米色'),
    OptionDef(value='other', label='其他'),
]

_FLOOR = [
    OptionDef(value='tile', label='地砖'),
    OptionDef(value='wood', label='地板'),
    OptionDef(value='carpet', label='地毯'),
    OptionDef(value='other', label='其他'),
]

_POWER = [
    OptionDef(value='enough', label='充足（4个以上）'),
    OptionDef(value='normal', label='一般（2-3个）'),
    OptionDef(value='tight', label='紧张（1个）'),
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

_BODY_TYPE = [
    OptionDef(value='thin', label='偏瘦'),
    OptionDef(value='standard', label='标准'),
    OptionDef(value='strong', label='偏壮'),
    OptionDef(value='plus', label='大码'),
]

_SKIN_TONE = [
    OptionDef(value='cool-white', label='冷白皮'),
    OptionDef(value='natural-white', label='自然白'),
    OptionDef(value='wheat', label='小麦色'),
    OptionDef(value='yellowish', label='偏黄'),
    OptionDef(value='dark', label='偏黑'),
]

_HAIR_COLOR = [
    OptionDef(value='black', label='黑色'),
    OptionDef(value='brown', label='棕色'),
    OptionDef(value='yellow', label='黄色'),
    OptionDef(value='other', label='其他'),
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

# 设备明细表列定义（第八节）
_EQUIPMENT_COLUMNS = [
    TableColumn(id='type', label='设备类型', placeholder='相机/镜头/主灯等'),
    TableColumn(id='model', label='品牌型号', placeholder='例：Sony A7M4'),
    TableColumn(id='qty', label='数量', placeholder='数量'),
    TableColumn(id='note', label='备注', placeholder='其他说明'),
]


# ──────────────────────────────────────────────────────────────
# 十章节定义（对照调研表逐章录入）
# ──────────────────────────────────────────────────────────────

SECTIONS: list[SectionDef] = [


    # ── 一、客户基础信息 ──
    SectionDef(
        id='customer', title='一、客户基础信息', order=1,
        fields=[
            FieldDef(id='brand', label='客户名称/品牌名', type='text', required=True,
                     placeholder='如：云裳'),
            FieldDef(id='contact', label='联系人姓名', type='text', required=True,
                     placeholder='联系人'),
            FieldDef(id='phone', label='联系电话', type='text', required=True,
                     placeholder='138****'),
            FieldDef(id='wechat', label='微信号', type='text', required=False,
                     placeholder='选填，便于后续沟通'),
            FieldDef(id='city', label='所在城市', type='text', required=False,
                     placeholder='选填，如需线下服务可匹配'),
            FieldDef(id='source', label='客户来源', type='choice-single', required=True,
                     options=_CUSTOMER_SOURCE),
            FieldDef(id='date', label='咨询日期', type='text', required=False,
                     placeholder='自动填写'),
        ],
    ),


    # ── 二、行业与品类信息 ──
    SectionDef(
        id='industry', title='二、行业与品类信息', order=2,
        hint='重要：行业与品类是向量匹配的核心依据，越精准越好。',
        fields=[
            FieldDef(id='category', label='行业大类', type='choice-single', required=True,
                     options=_INDUSTRY_CATEGORIES),
            FieldDef(id='subcategory', label='细分品类', type='text', required=True,
                     placeholder='例：高端香云纱女装、黄金珠宝、进口零食'),
            FieldDef(id='price_band', label='商品价格带', type='choice-single', required=True,
                     options=_PRICE_BAND),
            FieldDef(id='positioning', label='品牌定位', type='choice-single', required=True,
                     options=_POSITIONING),
            FieldDef(id='target_age', label='目标客群年龄', type='choice-single', required=True,
                     options=_AGE_GROUP),
            FieldDef(id='target_gender', label='目标客群性别', type='choice-single', required=True,
                     options=_GENDER),
            FieldDef(id='live_type', label='直播间类型', type='choice-single', required=True,
                     options=_LIVE_TYPE),
        ],
    ),


    # ── 三、直播间现状 ──（条件：has_room=yes 才填其余）
    SectionDef(
        id='status', title='三、直播间现状', order=3,
        fields=[
            FieldDef(id='has_room', label='是否已有直播间', type='choice-single', required=True,
                     options=_YES_NO),
            # 以下字段仅在 has_room=yes 时可见
            FieldDef(id='account', label='当前直播间账号', type='text', required=False,
                     placeholder='选填，可提供抖音号用于分析',
                     visible_if=VisibleIf(field_id='has_room', value='yes')),
            FieldDef(id='duration', label='开播时长', type='choice-single', required=False,
                     options=_BROADCAST_DURATION,
                     visible_if=VisibleIf(field_id='has_room', value='yes')),
            FieldDef(id='viewers', label='当前场均观看', type='choice-single', required=False,
                     options=_VIEWERS,
                     visible_if=VisibleIf(field_id='has_room', value='yes')),
            FieldDef(id='gmv', label='当前场均GMV', type='choice-single', required=False,
                     options=_GMV,
                     visible_if=VisibleIf(field_id='has_room', value='yes')),
            FieldDef(id='satisfaction', label='对现状是否满意', type='choice-single', required=False,
                     options=_SATISFACTION,
                     visible_if=VisibleIf(field_id='has_room', value='yes')),
            FieldDef(id='pain_points', label='主要痛点', type='choice-multi', required=False,
                     options=_PAIN_POINTS,
                     visible_if=VisibleIf(field_id='has_room', value='yes')),
            FieldDef(id='room_photo', label='直播间照片/截图', type='image', required=False,
                     visible_if=VisibleIf(field_id='has_room', value='yes')),
        ],
    ),


    # ── 四、场地条件信息 ──
    SectionDef(
        id='venue', title='四、场地条件信息', order=4,
        hint='重要：场地尺寸直接影响设备选型与布局方案，请尽量准确。',
        fields=[
            FieldDef(id='area', label='直播间面积', type='choice-single', required=True,
                     options=_AREA),
            FieldDef(id='size', label='具体尺寸（宽×深×高）', type='dimension', required=True,
                     dims=['宽', '深', '高'], unit='m'),
            FieldDef(id='shape', label='房间形状', type='choice-single', required=False,
                     options=_ROOM_SHAPE),
            FieldDef(id='window', label='窗户情况', type='choice-single', required=True,
                     options=_WINDOW),
            FieldDef(id='window_pos', label='窗户位置', type='choice-single', required=False,
                     options=_WINDOW_POS,
                     visible_if=VisibleIf(field_id='window', op='ne', value='none')),
            FieldDef(id='wall_color', label='墙面颜色', type='choice-single', required=False,
                     options=_WALL_COLOR),
            FieldDef(id='floor', label='地面材质', type='choice-single', required=False,
                     options=_FLOOR),
            FieldDef(id='power', label='电源点位', type='choice-single', required=False,
                     options=_POWER),
            FieldDef(id='renovation', label='是否允许装修', type='choice-single', required=True,
                     options=_RENOVATION),
            FieldDef(id='venue_photo', label='场地照片', type='image', required=False),
        ],
    ),


    # ── 五、预算范围信息 ──
    SectionDef(
        id='budget', title='五、预算范围信息', order=5,
        fields=[
            FieldDef(id='total', label='总预算范围', type='choice-single', required=True,
                     options=_TOTAL_BUDGET),
            FieldDef(id='equipment', label='其中设备预算', type='choice-single', required=True,
                     options=_EQUIP_BUDGET),
            FieldDef(id='decor', label='其中装修预算', type='choice-single', required=True,
                     options=_DECOR_BUDGET),
            FieldDef(id='flex', label='预算弹性', type='choice-single', required=False,
                     options=_BUDGET_FLEX),
            FieldDef(id='has_existing', label='是否已有部分设备', type='choice-single', required=True,
                     options=_YES_NO),
        ],
    ),


    # ── 六、商品与品牌视觉信息 ──
    SectionDef(
        id='product', title='六、商品与品牌视觉信息', order=6,
        hint='重要：商品与品牌信息是场景设计的核心依据。',
        fields=[
            FieldDef(id='main', label='主营商品类型', type='text', required=True,
                     placeholder='例：连衣裙、口红、翡翠手镯'),
            FieldDef(id='material', label='商品材质特点', type='text', required=False,
                     placeholder='例：丝绸光泽、金属质感、宝石火彩'),
            FieldDef(id='size_cat', label='商品尺寸', type='choice-single', required=True,
                     options=_PRODUCT_SIZE),
            FieldDef(id='theme_color', label='品牌主色调', type='text', required=False,
                     placeholder='有VI的请提供色值或参考图'),
            FieldDef(id='keywords', label='品牌风格关键词', type='text', required=True,
                     placeholder='3-5个关键词，例：国风、高端、雅致、轻奢、简约'),
            FieldDef(id='style_ref', label='喜欢的风格参考', type='text', required=False,
                     placeholder='可提供参考直播间账号或图片'),
            FieldDef(id='dislike_style', label='不喜欢的风格', type='text', required=False,
                     placeholder='明确避开的方向'),
            FieldDef(id='logo', label='品牌Logo/VI', type='image', required=False),
            FieldDef(id='sample_photo', label='商品样品图', type='image', required=False),
        ],
    ),


    # ── 七、主播信息 ──
    SectionDef(
        id='host', title='七、主播信息', order=7,
        fields=[
            FieldDef(id='count', label='主播人数', type='choice-single', required=True,
                     options=_HOST_COUNT),
            FieldDef(id='height', label='主播身高', type='dimension', required=True,
                     dims=['女主播', '男主播'], unit='cm'),
            FieldDef(id='body', label='主播体型', type='choice-single', required=False,
                     options=_BODY_TYPE),
            FieldDef(id='skin', label='主播肤色', type='choice-single', required=False,
                     options=_SKIN_TONE),
            FieldDef(id='hair', label='主播发色', type='choice-single', required=False,
                     options=_HAIR_COLOR),
            FieldDef(id='host_photo', label='主播形象照', type='image', required=False),
            FieldDef(id='movement', label='直播时是否走动', type='choice-single', required=True,
                     options=_MOVEMENT),
        ],
    ),


    # ── 八、现有设备情况 ──（table 类型，条件：budget.has_existing=yes）
    SectionDef(
        id='equipment', title='八、现有设备情况', order=8,
        hint='如果已有部分设备，请详细填写，系统会基于现有设备做参数优化。',
        fields=[
            # 本章节整体是否填写取决于第五章 has_existing 字段。
            # table 字段：每行一台设备，列 = 设备类型/品牌型号/数量/备注。
            FieldDef(
                id='inventory', label='现有设备明细', type='table', required=False,
                columns=_EQUIPMENT_COLUMNS,
            ),
        ],
    ),


    # ── 九、需求与目标 ──
    SectionDef(
        id='goal', title='九、需求与目标', order=9,
        fields=[
            FieldDef(id='core', label='核心需求', type='choice-single', required=True,
                     options=_CORE_NEED),
            FieldDef(id='focus', label='最看重的效果', type='choice-multi', required=False,
                     options=_FOCUS_EFFECT),
            FieldDef(id='expectation', label='预期达到的效果', type='text', required=False,
                     placeholder='客户的期望描述'),
            FieldDef(id='need_3d', label='是否需要3D效果图', type='choice-single', required=True,
                     options=_NEED_3D),
            FieldDef(id='deadline', label='期望交付时间', type='choice-single', required=True,
                     options=_DEADLINE),
            FieldDef(id='other', label='其他特殊要求', type='text', required=False,
                     placeholder='任何特殊需求都可以写'),
        ],
    ),


    # ── 十、客服备注 ──
    SectionDef(
        id='notes', title='十、客服备注', order=10,
        fields=[
            FieldDef(id='communication', label='客户沟通要点', type='text', required=False,
                     placeholder=''),
            FieldDef(id='focus_points', label='重点关注事项', type='text', required=False,
                     placeholder=''),
            FieldDef(id='judgment', label='客服初步判断', type='text', required=False,
                     placeholder=''),
            FieldDef(id='signature', label='客服签名', type='text', required=False,
                     placeholder=''),
            FieldDef(id='fill_date', label='填写日期', type='text', required=False,
                     placeholder=''),
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
- 能选填的尽量选填：信息越完整，生成的方案越精准
- 不确定的就写不确定：不要瞎猜，系统会按默认值处理
- 图片尽量多要：直播间照片、场地照片、商品照片，对方案生成帮助极大
- 风格关键词要具体：不要只写"好看"，要写"高级感""国风""轻奢"这类具体词

常见问题引导：
- 客户说"我也不知道要什么风格"：引导客户说几个喜欢的直播间账号，或者描述一下想要的感觉（亮一点/暗一点/暖一点/冷一点）
- 客户预算不明确：可以给几个档位让客户选，或者问"大概是想做普通的还是专业级的"
- 客户不知道自己设备型号：让客户拍设备照片，或者看设备上的标签
"""
