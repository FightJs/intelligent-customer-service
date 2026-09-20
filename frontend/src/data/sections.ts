/**
 * @generated 由 frontend/scripts/gen-schema.mjs 从 schema.json 生成，勿手改。
 * 改后端 schema 后：python -m backend.survey.export && npm run gen:schema
 */
import type { SectionDef, SectionId } from '../types/schema'

export const SECTIONS: SectionDef[] = [
  {
    "id": "customer",
    "title": "一、基础信息采集",
    "hint": "核心必填：用于方案归档与后续对接。",
    "order": 1,
    "skippable": false,
    "fields": [
      {
        "id": "brand",
        "label": "品牌/公司名称",
        "type": "text",
        "required": true,
        "question": "请问您的品牌或公司名称是什么？",
        "skippable": false,
        "askInFull": true,
        "placeholder": "如：跃步",
        "helpText": "填写说明：用于方案标题与正式归档，是生成专属方案的核心标识。"
      },
      {
        "id": "identity",
        "label": "客户身份",
        "type": "choice-multi",
        "required": true,
        "question": "请问您的身份是？主理人（老板）、主播、运营、其他，可多选。",
        "skippable": false,
        "askInFull": true,
        "options": [
          {
            "value": "owner",
            "label": "主理人（老板）"
          },
          {
            "value": "host",
            "label": "主播"
          },
          {
            "value": "operator",
            "label": "运营"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ],
        "helpText": "填写说明：可按实际职责多选，方便我们从对应使用视角整理方案。"
      },
      {
        "id": "contact",
        "label": "姓名",
        "type": "text",
        "required": true,
        "question": "方便留下您的姓名和联系电话吗？",
        "skippable": false,
        "askInFull": true,
        "placeholder": "联系人姓名",
        "helpText": "填写说明：方便我们后续对接方案细节，确保能第一时间给到您完整的方案内容。"
      },
      {
        "id": "phone",
        "label": "联系电话",
        "type": "text",
        "required": true,
        "question": "联系电话还没有记录，方便再补充一下吗？",
        "skippable": false,
        "askInFull": true,
        "placeholder": "138****",
        "helpText": "填写说明：方便我们后续对接方案细节，确保能第一时间给到您完整的方案内容。"
      },
      {
        "id": "source",
        "label": "了解渠道",
        "type": "choice-single",
        "required": true,
        "question": "您是通过哪个渠道了解到我们的？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：用于我们统计客户来源，优化服务渠道，也能帮您匹配对应渠道的专属服务资源。"
      },
      {
        "id": "wechat",
        "label": "微信号",
        "type": "text",
        "required": false,
        "question": "方便留下您的微信号吗？",
        "skippable": true,
        "askInFull": true,
        "placeholder": "选填，便于发送效果图和设备清单",
        "helpText": "填写说明：方便后续微信端给您发送方案效果图、设备清单等详细资料。"
      },
      {
        "id": "city",
        "label": "所在城市",
        "type": "text",
        "required": false,
        "question": "请问您所在的城市是哪里？",
        "skippable": true,
        "askInFull": true,
        "placeholder": "选填，如需线下服务可匹配资源",
        "helpText": "填写说明：如果您有线下服务需求，我们可以帮您匹配对应城市的落地资源。"
      }
    ]
  },
  {
    "id": "industry",
    "title": "二、行业与品类信息",
    "hint": "核心信息：用于匹配视觉方向。按当前业务要求，大类和细分品类允许跳过。",
    "order": 2,
    "skippable": false,
    "fields": [
      {
        "id": "category",
        "label": "行业大类",
        "type": "choice-single",
        "required": false,
        "question": "您的直播间主营什么行业大类？",
        "skippable": true,
        "askInFull": true,
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
            "value": "shoes",
            "label": "鞋靴"
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
        ],
        "helpText": "填写说明：不同行业的直播间视觉逻辑、商品展示方式差异极大，明确行业能帮您匹配最贴合的方案模板。"
      },
      {
        "id": "subcategory",
        "label": "细分品类",
        "type": "text",
        "required": false,
        "question": "更具体的细分品类是什么？",
        "skippable": true,
        "askInFull": true,
        "placeholder": "例：国产实战篮球鞋、高端香云纱女装、黄金珠宝、进口零食",
        "helpText": "填写示例：国产实战篮球鞋、高端香云纱女装、黄金珠宝、进口零食，越具体，生成的方案越精准。"
      },
      {
        "id": "price_band",
        "label": "商品价格带",
        "type": "choice-single",
        "required": true,
        "question": "您的商品价格带大致是多少？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：价格带直接决定直播间的档次定位、视觉风格方向，是方案设计的核心参考。"
      },
      {
        "id": "price_range_raw",
        "label": "用户原始商品价格范围",
        "type": "text",
        "required": false,
        "question": "（系统自动保留用户给出的具体价格范围）",
        "skippable": false,
        "askInFull": false,
        "helpText": "保留用户原话，避免区间归类后丢失精度。"
      },
      {
        "id": "positioning",
        "label": "品牌定位",
        "type": "choice-single",
        "required": true,
        "question": "您的品牌定位属于哪一类？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：品牌定位决定了直播间的视觉基调，避免方案风格和品牌调性脱节。"
      },
      {
        "id": "target_age",
        "label": "目标客群年龄",
        "type": "choice-single",
        "required": true,
        "question": "核心目标客群年龄主要集中在哪个区间？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：不同年龄层的色彩偏好、视觉审美差异很大，能帮您优化直播间的视觉吸引力。"
      },
      {
        "id": "target_gender",
        "label": "目标客群性别",
        "type": "choice-single",
        "required": true,
        "question": "目标客群的性别偏向是怎样的？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：针对性别优化视觉风格，能有效提升目标用户的停留意愿。"
      },
      {
        "id": "live_type",
        "label": "直播间类型",
        "type": "choice-single",
        "required": true,
        "question": "您的直播间属于哪种类型？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：不同类型的直播间，视觉设计、设备选型的标准完全不同，明确类型能避免方案跑偏。"
      }
    ]
  },
  {
    "id": "status",
    "title": "三、直播间现状",
    "hint": "选填：已有直播间时补充；没有直播间可直接跳过本模块。",
    "order": 3,
    "skippable": true,
    "fields": [
      {
        "id": "has_room",
        "label": "是否已有直播间",
        "type": "choice-single",
        "required": false,
        "question": "您目前已经有正在运营的直播间了吗？",
        "skippable": false,
        "askInFull": true,
        "options": [
          {
            "value": "yes",
            "label": "是"
          },
          {
            "value": "no",
            "label": "否"
          }
        ],
        "helpText": "填写说明：用于判断是否继续了解现有直播间情况；没有直播间时将直接进入后续模块。"
      },
      {
        "id": "room_photo",
        "label": "直播间照片/风格参考图",
        "type": "image",
        "required": false,
        "question": "方便上传当前直播间照片，或希望对比的直播间样式参考图吗？",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写说明：可直接用于方案优化校准，让生成的方案更贴合您的实际情况，无需文字描述，拍照即可。",
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
        "question": "目前大约开播多久了？",
        "skippable": true,
        "askInFull": true,
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
        "helpText": "填写说明：了解直播间运营阶段，辅助判断优化侧重点。",
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
        "question": "当前直播间的场均观看人数大概是多少？",
        "skippable": true,
        "askInFull": true,
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
        "helpText": "填写说明：帮您判断当前流量层级，针对性优化视觉引流方案。",
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
        "question": "当前直播间的场均GMV大概是多少？",
        "skippable": true,
        "askInFull": true,
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
        "helpText": "填写说明：结合经营数据，匹配适配的视觉投入方案。",
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
        "question": "您对当前直播间的整体现状满意吗？",
        "skippable": true,
        "askInFull": true,
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
        "helpText": "填写说明：了解主观感受，找准优化方向。",
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
        "question": "当前直播间最核心的痛点有哪些？",
        "skippable": true,
        "askInFull": true,
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
        "helpText": "填写说明：明确痛点后，我们的方案会优先针对您的问题做优化，精准解决您的需求。",
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
    "hint": "核心必填：场地条件直接决定设备选型与装修方案。",
    "order": 4,
    "skippable": false,
    "fields": [
      {
        "id": "area",
        "label": "直播间面积",
        "type": "choice-single",
        "required": true,
        "question": "您的直播间场地面积大概是多少？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：面积是直播间布局、设备选型的核心基础，能帮您规划最合理的空间利用方案。"
      },
      {
        "id": "size",
        "label": "具体尺寸（宽×深×高）",
        "type": "dimension",
        "required": false,
        "question": "方便提供场地的宽、深、高吗？",
        "skippable": true,
        "askInFull": true,
        "dims": [
          "宽",
          "深",
          "高"
        ],
        "unit": "m",
        "helpText": "填写示例：宽__m × 深__m × 高__m，尺寸越精准，方案的落地性越强；不方便测量可直接拍照上传。"
      },
      {
        "id": "window",
        "label": "窗户情况",
        "type": "choice-single",
        "required": true,
        "question": "场地的窗户情况是怎样的？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：窗户情况直接影响灯光方案的设计，避免自然光干扰直播画面效果。"
      },
      {
        "id": "window_pos",
        "label": "窗户位置",
        "type": "choice-single",
        "required": false,
        "question": "如果有窗户，窗户在主播的哪个位置？",
        "skippable": true,
        "askInFull": true,
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
        "helpText": "填写说明：用于灯光布光方案设计，规避逆光、杂光问题。",
        "visibleIf": {
          "fieldId": "window",
          "op": "ne",
          "value": "none"
        }
      },
      {
        "id": "renovation",
        "label": "是否允许装修",
        "type": "choice-single",
        "required": true,
        "question": "您的场地允许装修改动吗？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：明确装修权限，能帮您制定完全贴合场地情况的方案，避免方案无法落地。"
      },
      {
        "id": "venue_photo",
        "label": "场地多角度照片",
        "type": "image",
        "required": false,
        "question": "方便上传场地的多角度照片吗？",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写说明：能让我们更直观地了解场地情况，避免方案和实际场地不符，直接拍照上传即可，不用手动描述细节。"
      }
    ]
  },
  {
    "id": "budget",
    "title": "五、预算范围信息",
    "hint": "核心必填：用于控制方案成本与设备选型。",
    "order": 5,
    "skippable": false,
    "fields": [
      {
        "id": "total",
        "label": "总预算范围",
        "type": "choice-single",
        "required": true,
        "question": "本次直播间搭建或优化的总预算范围是多少？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：预算是方案设计的核心边界，能帮您制定性价比最高的方案，避免超支。"
      },
      {
        "id": "equipment",
        "label": "设备采购预算",
        "type": "choice-single",
        "required": true,
        "question": "总预算中，设备采购大概安排多少？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：用于相机、灯光等核心设备的选型匹配，确保设备预算和总预算匹配。"
      },
      {
        "id": "decor",
        "label": "装修装饰预算",
        "type": "choice-single",
        "required": true,
        "question": "总预算中，装修装饰大概安排多少？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：用于背景墙、装饰等装修内容的规划，确保装修方案在预算范围内。"
      },
      {
        "id": "flex",
        "label": "预算弹性",
        "type": "choice-single",
        "required": false,
        "question": "您的预算弹性如何？",
        "skippable": true,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：便于我们在方案中预留调整空间。"
      },
      {
        "id": "has_existing",
        "label": "是否已有部分设备",
        "type": "choice-single",
        "required": true,
        "question": "您目前已经有部分直播设备了吗？",
        "skippable": false,
        "askInFull": true,
        "options": [
          {
            "value": "yes",
            "label": "是"
          },
          {
            "value": "no",
            "label": "否"
          }
        ],
        "helpText": "填写说明：有设备的话我们会基于现有设备做优化，不用重复采购，帮您节省成本。"
      }
    ]
  },
  {
    "id": "product",
    "title": "六、商品与品牌视觉信息",
    "hint": "核心必填：商品与品牌信息是场景设计的依据。",
    "order": 6,
    "skippable": false,
    "fields": [
      {
        "id": "main",
        "label": "主营商品类型",
        "type": "text",
        "required": true,
        "question": "直播间的主营商品类型是什么？",
        "skippable": false,
        "askInFull": true,
        "placeholder": "例：实战篮球鞋、口红、翡翠手镯",
        "helpText": "填写示例：实战篮球鞋、口红、翡翠手镯，越具体越好。"
      },
      {
        "id": "size_cat",
        "label": "商品尺寸",
        "type": "choice-single",
        "required": true,
        "question": "您的商品尺寸属于哪一类？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：商品尺寸直接决定了展示方式、机位构图，能帮您优化商品的呈现效果。"
      },
      {
        "id": "keywords",
        "label": "品牌风格关键词",
        "type": "text",
        "required": true,
        "question": "可以说3到5个品牌风格关键词吗？",
        "skippable": false,
        "askInFull": true,
        "placeholder": "例：国风、高端、雅致、轻奢、简约",
        "helpText": "填写示例：国风、高端、雅致、轻奢、简约，越具体，方案风格越贴合。"
      },
      {
        "id": "style_ref",
        "label": "喜欢的直播间风格参考",
        "type": "text",
        "required": false,
        "question": "有喜欢的直播间风格参考吗？可以描述账号或直接上传截图。",
        "skippable": true,
        "askInFull": true,
        "placeholder": "可填写参考直播间账号或名称",
        "helpText": "填写说明：可提供参考直播间账号或截图图片，能让我们更精准地匹配您的审美偏好。"
      },
      {
        "id": "style_ref_image",
        "label": "风格参考截图",
        "type": "image",
        "required": false,
        "question": "方便上传喜欢的直播间截图吗？",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写说明：可提供参考直播间账号或截图图片，能让我们更精准地匹配您的审美偏好。"
      },
      {
        "id": "dislike_style",
        "label": "明确不喜欢的风格",
        "type": "text",
        "required": false,
        "question": "有没有您明确不喜欢的风格？",
        "skippable": true,
        "askInFull": true,
        "placeholder": "明确需要避开的方向",
        "helpText": "填写说明：明确避开的方向，避免生成的方案不符合您的审美。"
      },
      {
        "id": "brand_assets",
        "label": "品牌Logo/VI与商品样品图",
        "type": "image",
        "required": false,
        "question": "方便上传品牌Logo、VI或商品样品图吗？",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写说明：可将品牌元素融入背景设计，同时针对商品做专属的展示优化，让方案更贴合品牌，直接上传图片即可。"
      }
    ]
  },
  {
    "id": "benchmark",
    "title": "七、对标直播间参考",
    "hint": "选填：没有对标直播间可直接跳过本模块。",
    "order": 7,
    "skippable": true,
    "fields": [
      {
        "id": "has_benchmark",
        "label": "是否有对标直播间",
        "type": "choice-single",
        "required": false,
        "question": "您有想要对标的直播间吗？",
        "skippable": false,
        "askInFull": true,
        "options": [
          {
            "value": "yes",
            "label": "是"
          },
          {
            "value": "no",
            "label": "否"
          }
        ],
        "helpText": "填写说明：用于判断是否继续采集对标信息；没有对标直播间时将直接进入后续模块。"
      },
      {
        "id": "account_name",
        "label": "主对标账号/名称",
        "type": "text",
        "required": false,
        "question": "请发一下主对标直播间的账号、链接或截图。",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写说明：对标直播间是视觉风格匹配的核心参考，信息越完整，生成的方案越精准。",
        "visibleIf": {
          "fieldId": "has_benchmark",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "platform",
        "label": "主对标平台",
        "type": "choice-single",
        "required": false,
        "question": "这个主对标直播间在哪个平台？",
        "skippable": true,
        "askInFull": true,
        "options": [
          {
            "value": "douyin",
            "label": "抖音"
          },
          {
            "value": "taobao",
            "label": "淘宝直播"
          },
          {
            "value": "kuaishou",
            "label": "快手"
          },
          {
            "value": "wechat",
            "label": "视频号"
          },
          {
            "value": "xiaohongshu",
            "label": "小红书"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ],
        "helpText": "填写说明：不同平台的直播间风格差异很大，明确平台能避免方案和平台生态脱节。",
        "visibleIf": {
          "fieldId": "has_benchmark",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "likes",
        "label": "喜欢的方面",
        "type": "choice-multi",
        "required": false,
        "question": "您最喜欢这个直播间的哪些方面？",
        "skippable": true,
        "askInFull": true,
        "options": [
          {
            "value": "overall",
            "label": "整体风格"
          },
          {
            "value": "background",
            "label": "背景装修"
          },
          {
            "value": "lighting",
            "label": "灯光效果"
          },
          {
            "value": "composition",
            "label": "机位构图"
          },
          {
            "value": "display",
            "label": "商品展示"
          },
          {
            "value": "color",
            "label": "色彩搭配"
          },
          {
            "value": "other",
            "label": "其他"
          }
        ],
        "helpText": "填写说明：明确喜欢的点，我们会把这些优势融入到您的方案中，同时避免照搬短板。",
        "visibleIf": {
          "fieldId": "has_benchmark",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "screenshot",
        "label": "对标截图/图片",
        "type": "image",
        "required": false,
        "question": "方便上传对标直播间的截图吗？",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写说明：可直接用于向量化分析，提取核心视觉特征，让方案更贴合您的对标需求，截图拍照上传即可。",
        "visibleIf": {
          "fieldId": "has_benchmark",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "reference_link",
        "label": "对标直播间链接",
        "type": "text",
        "required": false,
        "question": "有对标直播间的链接可以补充吗？",
        "skippable": true,
        "askInFull": true,
        "placeholder": "可粘贴直播间或作品链接",
        "helpText": "填写说明：可直接用于向量化分析，提取核心视觉特征，让方案更贴合您的对标需求。",
        "visibleIf": {
          "fieldId": "has_benchmark",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "reference_mode",
        "label": "参考方式",
        "type": "choice-single",
        "required": false,
        "question": "您希望以哪种方式参考对标直播间？",
        "skippable": true,
        "askInFull": true,
        "options": [
          {
            "value": "optimize-primary",
            "label": "以主对标为基础优化"
          },
          {
            "value": "combine",
            "label": "综合多个对标优点"
          },
          {
            "value": "elements-only",
            "label": "只参考元素，不整体模仿"
          }
        ],
        "helpText": "填写说明：确定借鉴逻辑，控制方案原创程度。",
        "visibleIf": {
          "fieldId": "has_benchmark",
          "op": "eq",
          "value": "yes"
        }
      },
      {
        "id": "exact_copy",
        "label": "是否完全复刻",
        "type": "choice-single",
        "required": false,
        "question": "您需要尽量1:1复刻对标直播间吗？",
        "skippable": true,
        "askInFull": true,
        "options": [
          {
            "value": "yes",
            "label": "是，尽量1:1还原"
          },
          {
            "value": "no",
            "label": "否，参考风格但要有自己特色"
          }
        ],
        "helpText": "填写说明：区分复刻还是借鉴，把控方案输出方向。",
        "visibleIf": {
          "fieldId": "has_benchmark",
          "op": "eq",
          "value": "yes"
        }
      }
    ]
  },
  {
    "id": "host",
    "title": "八、主播信息",
    "hint": "选填：没有特殊主播适配需求可直接跳过本模块。",
    "order": 8,
    "skippable": true,
    "fields": [
      {
        "id": "count",
        "label": "主播人数",
        "type": "choice-single",
        "required": false,
        "question": "直播间通常有几位主播？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：主播人数会影响机位布局、构图设计，确保直播画面能适配所有主播。"
      },
      {
        "id": "movement",
        "label": "主播活动状态",
        "type": "choice-single",
        "required": false,
        "question": "直播时主播通常是坐着、站起还是会走动？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：影响镜头选型、空间布局，确保主播活动时画面始终稳定清晰。"
      },
      {
        "id": "profile",
        "label": "主播身高与体型补充",
        "type": "text",
        "required": false,
        "question": "主播的身高、体型等信息方便补充吗？",
        "skippable": true,
        "askInFull": true,
        "placeholder": "选填，用于机位高度和构图适配",
        "helpText": "填写说明：帮您优化机位高度、构图角度，让主播在画面里呈现更好的状态。"
      }
    ]
  },
  {
    "id": "equipment",
    "title": "九、现有设备情况",
    "hint": "选填：认识型号可文字填写；不认识型号可直接拍摄设备照片。",
    "order": 9,
    "skippable": true,
    "fields": [
      {
        "id": "inventory",
        "label": "现有设备文字明细",
        "type": "table",
        "required": false,
        "question": "可以描述现有设备的类型、型号和数量；不清楚型号也可以直接拍照上传。",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写指引：认识设备型号就填写品牌型号和数量；不认识型号无需猜测，可以直接拍摄上传设备照片，后端设备人员会帮您核对检测。",
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
          }
        ]
      },
      {
        "id": "equipment_photo",
        "label": "现有设备照片",
        "type": "image",
        "required": false,
        "question": "方便再拍摄并上传现有设备照片吗？",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写指引：不认识设备型号无需猜测，可以直接拍摄上传设备照片，后端设备人员会帮您核对检测。"
      }
    ],
    "visibleIf": {
      "fieldId": "budget.has_existing",
      "op": "eq",
      "value": "yes"
    }
  },
  {
    "id": "goal",
    "title": "十、核心需求与目标",
    "hint": "核心必填：用于明确服务范围与交付标准。",
    "order": 10,
    "skippable": false,
    "fields": [
      {
        "id": "core",
        "label": "核心需求",
        "type": "choice-single",
        "required": true,
        "question": "本次最核心的需求是什么？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：明确服务范围，确保我们给到的方案完全匹配您的需求，不做无效内容。"
      },
      {
        "id": "focus",
        "label": "最看重的效果",
        "type": "choice-multi",
        "required": true,
        "question": "您最看重直播间的哪些效果？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：明确核心优先级，我们会优先保障您最看重的效果落地。"
      },
      {
        "id": "need_3d",
        "label": "是否需要3D效果图",
        "type": "choice-single",
        "required": true,
        "question": "您需要提供3D效果图吗？",
        "skippable": false,
        "askInFull": true,
        "options": [
          {
            "value": "yes",
            "label": "需要"
          },
          {
            "value": "no",
            "label": "不需要"
          }
        ],
        "helpText": "填写说明：影响最终的交付内容，需要的话我们会同步生成多视角3D效果图。"
      },
      {
        "id": "deadline",
        "label": "期望交付时间",
        "type": "choice-single",
        "required": true,
        "question": "您期望什么时候完成交付？",
        "skippable": false,
        "askInFull": true,
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
        ],
        "helpText": "填写说明：便于项目排期，按时输出方案。"
      },
      {
        "id": "other",
        "label": "其他特殊要求",
        "type": "text",
        "required": false,
        "question": "还有其他特殊要求或参考图需要补充吗？可以文字说明或直接上传。",
        "skippable": true,
        "askInFull": true,
        "placeholder": "选填，任何特殊需求都可以写",
        "helpText": "填写说明：任何特殊需求都可以在这里说明，也可以直接上传参考图片，我们会在方案里优先满足。"
      },
      {
        "id": "other_reference",
        "label": "特殊要求补充参考图",
        "type": "image",
        "required": false,
        "question": "需要上传补充参考图吗？",
        "skippable": true,
        "askInFull": true,
        "helpText": "填写说明：任何特殊需求都可以在这里说明，也可以直接上传参考图片，我们会在方案里优先满足。"
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
  "benchmark",
  "host",
  "equipment",
  "goal"
] as SectionId[]

export const SECTION_BY_ID: Record<SectionId, SectionDef> = Object.fromEntries(
  SECTIONS.map((s) => [s.id, s]),
) as Record<SectionId, SectionDef>
