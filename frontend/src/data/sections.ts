/**
 * @generated 由 frontend/scripts/gen-schema.mjs 从 schema.json 生成，勿手改。
 * 改后端 schema 后：python -m backend.survey.export && npm run gen:schema
 */
import type { SectionDef, SectionId } from '../types/schema'

export const SECTIONS: SectionDef[] = [
  {
    "id": "customer",
    "title": "一、客户基础信息",
    "hint": "",
    "order": 1,
    "fields": [
      {
        "id": "brand",
        "label": "客户名称/品牌名",
        "type": "text",
        "required": true,
        "placeholder": "如：云裳"
      },
      {
        "id": "contact",
        "label": "联系人姓名",
        "type": "text",
        "required": true,
        "placeholder": "联系人"
      },
      {
        "id": "phone",
        "label": "联系电话",
        "type": "text",
        "required": true,
        "placeholder": "138****"
      },
      {
        "id": "wechat",
        "label": "微信号",
        "type": "text",
        "required": false,
        "placeholder": "选填，便于后续沟通"
      },
      {
        "id": "city",
        "label": "所在城市",
        "type": "text",
        "required": false,
        "placeholder": "选填，如需线下服务可匹配"
      },
      {
        "id": "source",
        "label": "客户来源",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "douyin",
            "label": "抖音直播"
          },
          {
            "value": "ads",
            "label": "信息流广告"
          },
          {
            "value": "referral",
            "label": "朋友推荐"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ]
      },
      {
        "id": "date",
        "label": "咨询日期",
        "type": "text",
        "required": false,
        "placeholder": "自动填写"
      }
    ]
  },
  {
    "id": "industry",
    "title": "二、行业与品类信息",
    "hint": "重要：行业与品类是向量匹配的核心依据，越精准越好。",
    "order": 2,
    "fields": [
      {
        "id": "category",
        "label": "行业大类",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "women",
            "label": "女装"
          },
          {
            "value": "men",
            "label": "男装"
          },
          {
            "value": "beauty",
            "label": "美妆"
          },
          {
            "value": "food",
            "label": "食品"
          },
          {
            "value": "jewelry",
            "label": "珠宝"
          },
          {
            "value": "home",
            "label": "家居"
          },
          {
            "value": "digital",
            "label": "数码"
          },
          {
            "value": "baby",
            "label": "母婴"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ]
      },
      {
        "id": "subcategory",
        "label": "细分品类",
        "type": "text",
        "required": true,
        "placeholder": "例：高端香云纱女装、黄金珠宝、进口零食"
      },
      {
        "id": "price_band",
        "label": "商品价格带",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "low",
            "label": "低客单（<100元）"
          },
          {
            "value": "mid",
            "label": "中客单（100-500元）"
          },
          {
            "value": "high",
            "label": "高客单（500-2000元）"
          },
          {
            "value": "ultra",
            "label": "超高客单（>2000元）"
          }
        ]
      },
      {
        "id": "positioning",
        "label": "品牌定位",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "mass",
            "label": "平价大众"
          },
          {
            "value": "value",
            "label": "性价比"
          },
          {
            "value": "mid-high",
            "label": "中高端"
          },
          {
            "value": "luxury",
            "label": "轻奢/高端"
          },
          {
            "value": "premium",
            "label": "奢侈品"
          }
        ]
      },
      {
        "id": "target_age",
        "label": "目标客群年龄",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "18-25",
            "label": "18-25岁"
          },
          {
            "value": "25-35",
            "label": "25-35岁"
          },
          {
            "value": "35-45",
            "label": "35-45岁"
          },
          {
            "value": "45+",
            "label": "45岁以上"
          }
        ]
      },
      {
        "id": "target_gender",
        "label": "目标客群性别",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "female",
            "label": "女性为主"
          },
          {
            "value": "male",
            "label": "男性为主"
          },
          {
            "value": "balanced",
            "label": "男女均衡"
          }
        ]
      },
      {
        "id": "live_type",
        "label": "直播间类型",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "influencer",
            "label": "达人带货"
          },
          {
            "value": "brand",
            "label": "品牌自播"
          },
          {
            "value": "factory",
            "label": "工厂店播"
          },
          {
            "value": "ip",
            "label": "个人IP"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ]
      }
    ]
  },
  {
    "id": "status",
    "title": "三、直播间现状",
    "hint": "",
    "order": 3,
    "fields": [
      {
        "id": "has_room",
        "label": "是否已有直播间",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "yes",
            "label": "是"
          },
          {
            "value": "no",
            "label": "否"
          }
        ]
      },
      {
        "id": "account",
        "label": "当前直播间账号",
        "type": "text",
        "required": false,
        "placeholder": "选填，可提供抖音号用于分析",
        "visibleIf": {
          "fieldId": "has_room",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "duration",
        "label": "开播时长",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "none",
            "label": "未开播"
          },
          {
            "value": "1m",
            "label": "1个月内"
          },
          {
            "value": "1-3m",
            "label": "1-3个月"
          },
          {
            "value": "3-6m",
            "label": "3-6个月"
          },
          {
            "value": "6m+",
            "label": "6个月以上"
          }
        ],
        "visibleIf": {
          "fieldId": "has_room",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "viewers",
        "label": "当前场均观看",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "<500",
            "label": "<500人"
          },
          {
            "value": "500-2k",
            "label": "500-2000人"
          },
          {
            "value": "2k-10k",
            "label": "2000-1万人"
          },
          {
            "value": "10k+",
            "label": "1万人以上"
          }
        ],
        "visibleIf": {
          "fieldId": "has_room",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "gmv",
        "label": "当前场均GMV",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "<5k",
            "label": "<5000元"
          },
          {
            "value": "5k-2w",
            "label": "5000-2万"
          },
          {
            "value": "2w-10w",
            "label": "2万-10万"
          },
          {
            "value": "10w+",
            "label": "10万以上"
          }
        ],
        "visibleIf": {
          "fieldId": "has_room",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "satisfaction",
        "label": "对现状是否满意",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "very_bad",
            "label": "很不满意"
          },
          {
            "value": "bad",
            "label": "不太满意"
          },
          {
            "value": "neutral",
            "label": "一般"
          },
          {
            "value": "good",
            "label": "比较满意"
          },
          {
            "value": "very_good",
            "label": "非常满意"
          }
        ],
        "visibleIf": {
          "fieldId": "has_room",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "pain_points",
        "label": "主要痛点",
        "type": "choice-multi",
        "required": false,
        "options": [
          {
            "value": "traffic",
            "label": "流量少"
          },
          {
            "value": "retention",
            "label": "留不住人"
          },
          {
            "value": "conversion",
            "label": "转化率低"
          },
          {
            "value": "visual",
            "label": "画面不好看"
          },
          {
            "value": "equipment",
            "label": "设备不会调"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ],
        "visibleIf": {
          "fieldId": "has_room",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "room_photo",
        "label": "直播间照片/截图",
        "type": "image",
        "required": false,
        "visibleIf": {
          "fieldId": "has_room",
          "op": "eq",
          "value": "yes"
        }
      }
    ]
  },
  {
    "id": "venue",
    "title": "四、场地条件信息",
    "hint": "重要：场地尺寸直接影响设备选型与布局方案，请尽量准确。",
    "order": 4,
    "fields": [
      {
        "id": "area",
        "label": "直播间面积",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "<10",
            "label": "<10㎡"
          },
          {
            "value": "10-20",
            "label": "10-20㎡"
          },
          {
            "value": "20-30",
            "label": "20-30㎡"
          },
          {
            "value": "30-50",
            "label": "30-50㎡"
          },
          {
            "value": "50+",
            "label": "50㎡以上"
          }
        ]
      },
      {
        "id": "size",
        "label": "具体尺寸（宽×深×高）",
        "type": "dimension",
        "required": true,
        "dims": [
          "宽",
          "深",
          "高"
        ],
        "unit": "m"
      },
      {
        "id": "shape",
        "label": "房间形状",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "rect",
            "label": "长方形"
          },
          {
            "value": "square",
            "label": "正方形"
          },
          {
            "value": "l-shape",
            "label": "L型"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ]
      },
      {
        "id": "window",
        "label": "窗户情况",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "none",
            "label": "无窗户"
          },
          {
            "value": "coverable",
            "label": "有窗户但可遮挡"
          },
          {
            "value": "uncoverable",
            "label": "有窗户无法遮挡"
          }
        ]
      },
      {
        "id": "window_pos",
        "label": "窗户位置",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "behind",
            "label": "主播背后"
          },
          {
            "value": "front",
            "label": "主播正面"
          },
          {
            "value": "left",
            "label": "主播左侧"
          },
          {
            "value": "right",
            "label": "主播右侧"
          }
        ],
        "visibleIf": {
          "fieldId": "window",
          "op": "ne",
          "value": "none"
        }
      },
      {
        "id": "wall_color",
        "label": "墙面颜色",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "white",
            "label": "白色"
          },
          {
            "value": "gray",
            "label": "灰色"
          },
          {
            "value": "beige",
            "label": "米色"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ]
      },
      {
        "id": "floor",
        "label": "地面材质",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "tile",
            "label": "地砖"
          },
          {
            "value": "wood",
            "label": "地板"
          },
          {
            "value": "carpet",
            "label": "地毯"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ]
      },
      {
        "id": "power",
        "label": "电源点位",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "enough",
            "label": "充足（4个以上）"
          },
          {
            "value": "normal",
            "label": "一般（2-3个）"
          },
          {
            "value": "tight",
            "label": "紧张（1个）"
          }
        ]
      },
      {
        "id": "renovation",
        "label": "是否允许装修",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "major",
            "label": "可以大改"
          },
          {
            "value": "minor",
            "label": "可以小改"
          },
          {
            "value": "none",
            "label": "不能改动"
          },
          {
            "value": "unsure",
            "label": "不确定"
          }
        ]
      },
      {
        "id": "venue_photo",
        "label": "场地照片",
        "type": "image",
        "required": false
      }
    ]
  },
  {
    "id": "budget",
    "title": "五、预算范围信息",
    "hint": "",
    "order": 5,
    "fields": [
      {
        "id": "total",
        "label": "总预算范围",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "<1w",
            "label": "1万以下"
          },
          {
            "value": "1-3w",
            "label": "1-3万"
          },
          {
            "value": "3-5w",
            "label": "3-5万"
          },
          {
            "value": "5-10w",
            "label": "5-10万"
          },
          {
            "value": "10-20w",
            "label": "10-20万"
          },
          {
            "value": "20w+",
            "label": "20万以上"
          }
        ]
      },
      {
        "id": "equipment",
        "label": "其中设备预算",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "<5k",
            "label": "5千以下"
          },
          {
            "value": "5k-1w",
            "label": "5千-1万"
          },
          {
            "value": "1-2w",
            "label": "1-2万"
          },
          {
            "value": "2-5w",
            "label": "2-5万"
          },
          {
            "value": "5w+",
            "label": "5万以上"
          }
        ]
      },
      {
        "id": "decor",
        "label": "其中装修预算",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "<5k",
            "label": "5千以下"
          },
          {
            "value": "5k-1w",
            "label": "5千-1万"
          },
          {
            "value": "1-3w",
            "label": "1-3万"
          },
          {
            "value": "3-5w",
            "label": "3-5万"
          },
          {
            "value": "5w+",
            "label": "5万以上"
          }
        ]
      },
      {
        "id": "flex",
        "label": "预算弹性",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "tight",
            "label": "很紧张，不能超"
          },
          {
            "value": "some",
            "label": "有10%左右浮动空间"
          },
          {
            "value": "flexible",
            "label": "比较灵活，效果优先"
          }
        ]
      },
      {
        "id": "has_existing",
        "label": "是否已有部分设备",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "yes",
            "label": "是"
          },
          {
            "value": "no",
            "label": "否"
          }
        ]
      }
    ]
  },
  {
    "id": "product",
    "title": "六、商品与品牌视觉信息",
    "hint": "重要：商品与品牌信息是场景设计的核心依据。",
    "order": 6,
    "fields": [
      {
        "id": "main",
        "label": "主营商品类型",
        "type": "text",
        "required": true,
        "placeholder": "例：连衣裙、口红、翡翠手镯"
      },
      {
        "id": "material",
        "label": "商品材质特点",
        "type": "text",
        "required": false,
        "placeholder": "例：丝绸光泽、金属质感、宝石火彩"
      },
      {
        "id": "size_cat",
        "label": "商品尺寸",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "tiny",
            "label": "很小（首饰类）"
          },
          {
            "value": "small",
            "label": "小（美妆类）"
          },
          {
            "value": "medium",
            "label": "中（服装类）"
          },
          {
            "value": "large",
            "label": "大（家居类）"
          }
        ]
      },
      {
        "id": "theme_color",
        "label": "品牌主色调",
        "type": "text",
        "required": false,
        "placeholder": "有VI的请提供色值或参考图"
      },
      {
        "id": "keywords",
        "label": "品牌风格关键词",
        "type": "text",
        "required": true,
        "placeholder": "3-5个关键词，例：国风、高端、雅致、轻奢、简约"
      },
      {
        "id": "style_ref",
        "label": "喜欢的风格参考",
        "type": "text",
        "required": false,
        "placeholder": "可提供参考直播间账号或图片"
      },
      {
        "id": "dislike_style",
        "label": "不喜欢的风格",
        "type": "text",
        "required": false,
        "placeholder": "明确避开的方向"
      },
      {
        "id": "logo",
        "label": "品牌Logo/VI",
        "type": "image",
        "required": false
      },
      {
        "id": "sample_photo",
        "label": "商品样品图",
        "type": "image",
        "required": false
      }
    ]
  },
  {
    "id": "host",
    "title": "七、主播信息",
    "hint": "",
    "order": 7,
    "fields": [
      {
        "id": "count",
        "label": "主播人数",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "1",
            "label": "1人"
          },
          {
            "value": "2",
            "label": "2人"
          },
          {
            "value": "3+",
            "label": "3人及以上"
          }
        ]
      },
      {
        "id": "height",
        "label": "主播身高",
        "type": "dimension",
        "required": true,
        "dims": [
          "女主播",
          "男主播"
        ],
        "unit": "cm"
      },
      {
        "id": "body",
        "label": "主播体型",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "thin",
            "label": "偏瘦"
          },
          {
            "value": "standard",
            "label": "标准"
          },
          {
            "value": "strong",
            "label": "偏壮"
          },
          {
            "value": "plus",
            "label": "大码"
          }
        ]
      },
      {
        "id": "skin",
        "label": "主播肤色",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "cool-white",
            "label": "冷白皮"
          },
          {
            "value": "natural-white",
            "label": "自然白"
          },
          {
            "value": "wheat",
            "label": "小麦色"
          },
          {
            "value": "yellowish",
            "label": "偏黄"
          },
          {
            "value": "dark",
            "label": "偏黑"
          }
        ]
      },
      {
        "id": "hair",
        "label": "主播发色",
        "type": "choice-single",
        "required": false,
        "options": [
          {
            "value": "black",
            "label": "黑色"
          },
          {
            "value": "brown",
            "label": "棕色"
          },
          {
            "value": "yellow",
            "label": "黄色"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ]
      },
      {
        "id": "host_photo",
        "label": "主播形象照",
        "type": "image",
        "required": false
      },
      {
        "id": "movement",
        "label": "直播时是否走动",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "sit",
            "label": "基本坐着"
          },
          {
            "value": "occasional",
            "label": "偶尔站起"
          },
          {
            "value": "frequent",
            "label": "经常走动"
          },
          {
            "value": "wide",
            "label": "大范围移动"
          }
        ]
      }
    ]
  },
  {
    "id": "equipment",
    "title": "八、现有设备情况",
    "hint": "如果已有部分设备，请详细填写，系统会基于现有设备做参数优化。",
    "order": 8,
    "fields": [
      {
        "id": "inventory",
        "label": "现有设备明细",
        "type": "table",
        "required": false,
        "columns": [
          {
            "id": "type",
            "label": "设备类型",
            "placeholder": "相机/镜头/主灯等"
          },
          {
            "id": "model",
            "label": "品牌型号",
            "placeholder": "例：Sony A7M4"
          },
          {
            "id": "qty",
            "label": "数量",
            "placeholder": "数量"
          },
          {
            "id": "note",
            "label": "备注",
            "placeholder": "其他说明"
          }
        ]
      }
    ]
  },
  {
    "id": "goal",
    "title": "九、需求与目标",
    "hint": "",
    "order": 9,
    "fields": [
      {
        "id": "core",
        "label": "核心需求",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "new",
            "label": "全新搭建直播间"
          },
          {
            "value": "optimize",
            "label": "优化现有直播间"
          },
          {
            "value": "tune",
            "label": "只调设备参数"
          },
          {
            "value": "decor",
            "label": "只做装修设计"
          },
          {
            "value": "full",
            "label": "全套方案"
          }
        ]
      },
      {
        "id": "focus",
        "label": "最看重的效果",
        "type": "choice-multi",
        "required": false,
        "options": [
          {
            "value": "premium-look",
            "label": "画面高级感"
          },
          {
            "value": "host-look",
            "label": "主播好看"
          },
          {
            "value": "product-quality",
            "label": "商品质感"
          },
          {
            "value": "pro-lighting",
            "label": "灯光专业"
          },
          {
            "value": "value",
            "label": "性价比高"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ]
      },
      {
        "id": "expectation",
        "label": "预期达到的效果",
        "type": "text",
        "required": false,
        "placeholder": "客户的期望描述"
      },
      {
        "id": "need_3d",
        "label": "是否需要3D效果图",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "yes",
            "label": "需要"
          },
          {
            "value": "no",
            "label": "不需要"
          }
        ]
      },
      {
        "id": "deadline",
        "label": "期望交付时间",
        "type": "choice-single",
        "required": true,
        "options": [
          {
            "value": "3d",
            "label": "3天内"
          },
          {
            "value": "1w",
            "label": "一周内"
          },
          {
            "value": "2w",
            "label": "两周内"
          },
          {
            "value": "flexible",
            "label": "不着急"
          }
        ]
      },
      {
        "id": "other",
        "label": "其他特殊要求",
        "type": "text",
        "required": false,
        "placeholder": "任何特殊需求都可以写"
      }
    ]
  },
  {
    "id": "notes",
    "title": "十、客服备注",
    "hint": "",
    "order": 10,
    "fields": [
      {
        "id": "communication",
        "label": "客户沟通要点",
        "type": "text",
        "required": false
      },
      {
        "id": "focus_points",
        "label": "重点关注事项",
        "type": "text",
        "required": false
      },
      {
        "id": "judgment",
        "label": "客服初步判断",
        "type": "text",
        "required": false
      },
      {
        "id": "signature",
        "label": "客服签名",
        "type": "text",
        "required": false
      },
      {
        "id": "fill_date",
        "label": "填写日期",
        "type": "text",
        "required": false
      }
    ]
  }
] as SectionDef[]

export const SECTION_ORDER: SectionId[] = [
  "customer",
  "industry",
  "status",
  "venue",
  "budget",
  "product",
  "host",
  "equipment",
  "goal",
  "notes"
] as SectionId[]

export const SECTION_BY_ID: Record<SectionId, SectionDef> = Object.fromEntries(
  SECTIONS.map((s) => [s.id, s]),
) as Record<SectionId, SectionDef>
