# F3 Spec — 360 预览图生成 Skill

> 管线阶段：`preview_images`。基于 F2 的 `plan.json` / `scene_card` 生成 ≥3 张多机位连贯预览图。
>
> 关联：
> - 方案真相源：`spec-f2-plan-document-skill.md`
> - 视频：`spec-f4-preview-video-skill.md`

---

## 1. 产品语义：「三张 360 预览图」

**不是**几何等距柱状（equirectangular）真全景。

落地定义：**同一场景、三机位连贯静帧**，覆盖直播间 360° 空间信息：

| 文件 | 机位 | 角度 | 画面重点 |
|------|------|------|----------|
| `preview_front.png` | 正面主视角（主播位） | 0° | 主机构图、商品区、背景墙 |
| `preview_left.png` | 左侧 | 120° | 布光设备、背景层次 |
| `preview_rear.png` | 背面/右侧 | 240° | 线材收纳、空间纵深、动线 |

真 360 全景 API 几何不稳，列为实验项，不进主路径。

---

## 2. 目标与边界

### 2.1 目标

1. 从 `scene_card` 确定性组装 prompt（禁止自由发挥设备/风格）
2. 单次组图任务产出 3 张风格连贯图
3. 立即落盘，记录 seed / 模型 / 成本，可复现

### 2.2 明确不做

| 不做 | 原因 |
|------|------|
| 真 equirectangular 360 全景 | 国内 API 几何不稳 |
| 用户任意风格自由生成 | 以 plan.json 为准 |
| 修图 / 局部重绘编辑器 | 超出管线范围 |
| 人物主播肖像定制 | 肖像权；默认空场景或远景人形 |
| 在图中渲染文字/logo | 生成模型文字不可靠；品牌元素走背景色块 |

---

## 3. 选型

| 项 | 主选 | 备选 | 理由 |
|----|------|------|------|
| 平台 | 阿里 **DashScope（百炼）** | 火山方舟 | 与 embedding/视频同账号 |
| 模型 | **万相 2.7 文生图 / 组图**（`wan2.7-image` 系列） | qwen-image；可灵图片 | 支持多图一致性相关参数 |
| 一致性 | `seed` + `color_palette` + 组图/sequential 模式（若模型提供） | 固定 seed 串行 3 次 | 三机位同房间 |
| 分辨率 | standard：2K；draft：1K；high：4K | | |
| 调用 | 异步任务 + 轮询（同步仅 draft） | | |
| 失败备选 | qwen-image → kling-v3-image | | |

> 实现时以 DashScope 控制台**当前可用模型 ID** 为准；上表模型名为能力档位，配置化：`IMAGE_MODEL`。

---

## 4. 输入契约

```python
class PreviewImagesInput(BaseModel):
    skill: Literal['preview_images'] = 'preview_images'
    pipeline_run_id: str
    plan_json_path: str                 # F2 产物
    image_count: int = 3                # 产品要求 ≥3
    quality: Literal['draft', 'standard', 'high'] = 'standard'
    allow_partial: bool = True
```

### 4.1 SceneCard（来自 F2，只读）

```python
class SceneCard(BaseModel):
    room_size_band: str          # small|medium|large|xlarge
    style_keywords: list[str]    # 国风/高端/…
    color_palette: list[str]     # hex 列表
    color_temp: str              # 4000K
    furniture: list[str]
    lighting_fixtures: list[str]
    product_category: str        # 女装
    camera_angles: list[str]     # front/left/rear
    forbidden: list[str]         # 文字水印、品牌logo
```

---

## 5. 处理流水线

```text
1. Load        读 plan.json，校验 scene_card 完整
2. Prompt      按机位模板组装 3 条 prompt（中英混合，见 §6）
3. Submit      提交 DashScope 异步生图任务（优先组图；失败降串行）
4. Poll        轮询至完成/失败/超时（≤180s）
5. Download    URL 24h 过期 → 立即落盘
6. Verify      可读、尺寸、非全黑；写 metadata
7. Persist     artifacts + skill_runs
```

---

## 6. Prompt 模板

### 6.1 公共锁（每条 prompt 必含）

```text
same room, same furniture set, same lighting setup, same color palette {palette},
professional livestream studio interior, photorealistic, no text, no watermark, no logo,
{style_keywords} style, room size {room_size_band}, product category {product_category},
lighting: {lighting_fixtures}, furniture: {furniture}, color temperature {color_temp}
```

### 6.2 机位差异段

| 角度 | 额外描述 |
|------|----------|
| front | `camera at host position, facing product display wall, front view of livestream set` |
| left | `camera at left side 120 degrees, show key lights, softboxes, background layers` |
| rear | `camera at rear-right 240 degrees, show cable management, walking path, depth of room` |

### 6.3 负向/禁止

将 `scene_card.forbidden` 转为 negative 提示或后置过滤说明（模型不支持 negative 时写入正向「no …」）。

### 6.4 一致性参数

| 参数 | 用法 |
|------|------|
| `seed` | 三图共用；生成后写入 metadata，重 roll 时可固定 |
| `color_palette` | 来自 scene_card |
| 组图/sequential | 若当前 IMAGE_MODEL 支持，一次任务出 3 张；否则串行 3 次同 seed |

---

## 7. 输出契约

```python
class PreviewImageItem(BaseModel):
    angle: Literal['front', 'left', 'rear']
    path: str
    url_source: str | None
    seed: int | None
    width: int
    height: int
    sha256: str
    model: str
    cost_cny: float

class PreviewImagesOutput(BaseModel):
    skill: Literal['preview_images']
    status: Literal['succeeded', 'partial', 'failed']
    images: list[PreviewImageItem]
    seed_used: int | None
    model: str
    total_cost_cny: float
    warnings: list[str]
    error: str | None = None
```

产物路径：

```text
data/artifacts/{pipeline_run_id}/images/preview_front.png
data/artifacts/{pipeline_run_id}/images/preview_left.png
data/artifacts/{pipeline_run_id}/images/preview_rear.png
data/artifacts/{pipeline_run_id}/images/manifest.json
```

---

## 8. 降级与重试

| 场景 | 行为 |
|------|------|
| 组图任务失败 | 固定 seed 串行 3 次单图 |
| 主模型失败 | 切备选模型一次 |
| 仅成功 1–2 张 | `partial`；允许 F4（至少 1 张）；F5 标注缺失机位 |
| 全失败 | `failed`；F5 可出「无图交付包」 |
| 图全黑/损坏 | 丢弃并重试（最多再 2 次） |
| 超时 >180s | failed，可人工重试 |

重 roll 策略（产品建议，默认关闭）：

- 每 pipeline_run 免费 1 次用户触发重 roll（`POST .../retry` skill=preview_images）
- 重 roll 使用**新 seed**，旧图保留为历史 artifact

---

## 9. 成本与时延

| 档位 | 估算（3 张） | 时延 |
|------|--------------|------|
| draft | ~0.3–1 元 | 10–30s |
| standard | ~1–3 元 | 20–60s |
| high | ~3–8 元 | 40–120s |

超时预算：≤180s。

---

## 10. 幂等

- 同 `pipeline_run_id` 已有 3 张成功图 → 复用
- `partial` 重试只补缺失机位，不重复已有成功图（除非 force）

---

## 11. 验收清单

- [ ] 单次（或降级串行）产出 ≥3 张，角度标签正确
- [ ] 三张图风格/色板/家具明显连贯（人工抽检）
- [ ] 无文字水印/乱码 logo
- [ ] 落盘 + sha256 + seed 可复现
- [ ] partial 时 F4/F5 能正确处理缺失
- [ ] mock DashScope 单测进 CI

---

## 12. 开放问题

1. 是否允许用户免费重 roll 1 次？（建议：是，计入日限额）
2. 是否生成有人形主播？建议默认无人，可选远景剪影。
3. 图片是否打品牌水印角标？建议后处理加，不靠生成模型。
