# F4 Spec — 预览视频生成 Skill

> 管线阶段：`preview_video`。基于 F2 方案与 F3 静帧，生成 5–15s 直播间环绕/漫游预览视频。
>
> 关联：
> - 方案：`spec-f2-plan-document-skill.md`
> - 首帧图：`spec-f3-preview-images-skill.md`
> - 汇总：`spec-f5-final-package-skill.md`

---

## 1. 目标与边界

### 1.1 目标

1. 以 F3 主视觉帧为起点，图生视频（i2v）
2. 产出可播放 mp4，表达空间尺度、布光氛围、动线
3. 异步执行，落盘并记录模型/成本/源图

### 1.2 明确不做

| 不做 | 原因 |
|------|------|
| 多镜头剪辑成片 | 需剪辑工作流 |
| 专业配音 / BGM 版权音乐 | 超出范围；默认无声 |
| 文生视频无图直接生成 | 与三机位静帧一致性差 |
| 超过 15s 长片 | 成本与时延不可控 |
| 4K 视频 | 当前 API 成本高，默认 720P/1080P |

---

## 2. 选型

| 项 | 主选 | 备选 | 理由 |
|----|------|------|------|
| 平台 | 阿里 **DashScope（百炼）** | 火山方舟（长视频补充） | 统一账号 |
| 模型 | **万相 2.7 图生视频** | 可灵视频；万相 2.6 flash（成本敏感） | i2v 保持首帧一致性 |
| 镜头语言 | prompt：`slow orbit / cinematic interior walkthrough` | 首尾帧插值（进阶） | |
| 调用 | 异步任务 + 轮询 | | 时延 1–4 分钟 |
| 产物 | mp4 | | |

配置化：`VIDEO_MODEL`。实现时以控制台当前可用模型 ID 为准。

---

## 3. 输入契约

```python
class PreviewVideoInput(BaseModel):
    skill: Literal['preview_video'] = 'preview_video'
    pipeline_run_id: str
    plan_json_path: str
    images: list[dict]              # F3 产物，至少 1 张
    duration_sec: int = 8           # 允许 5–15
    resolution: Literal['720P', '1080P'] = '720P'
    source_angle: Literal['front', 'left', 'rear'] = 'front'
```

### 3.1 首帧选择规则

1. 默认 `front`（主视角）
2. front 缺失 → `left` → `rear`
3. 无任何可用图 → 直接 `failed`（F5 出无视频包）

---

## 4. 处理流水线

```text
1. Select     选主视觉帧 + 读 scene_card
2. Prompt     组装 motion prompt（见 §5）
3. Submit     DashScope i2v 异步任务（duration / resolution / 无声）
4. Poll       轮询 ≤300s
5. Download   mp4 落盘（URL 过期前）
6. Verify     可读、时长、分辨率（可选 ffprobe）
7. Persist    artifact + metadata + skill_runs
```

---

## 5. Motion Prompt

以首帧图为锚的 i2v motion prompt，禁止按文生视频方式重述整个场景。

```text
以给定首帧图为唯一起点，严格保持画面中的房间结构、家具布置、灯具位置与色彩不变。
{camera_move_by_source_angle}。
专业直播间室内，{style_keywords}风格，色调 {color_palette}，可见 {furniture} 与 {lighting_fixtures}。
色温 {color_temp}，商品品类 {product_category}，{room_size_band} 房间尺度。
灯光稳定无闪烁，画面干净专业，无人物特写，无文字，无水印，无 logo。
{不要出现 forbidden...}
镜头运动平滑电影感，时长约 {duration_sec} 秒，画质 {resolution}。
```

镜头运动按首帧机位：

| source_angle | 镜头运动 |
|--------------|----------|
| front | 正机位缓慢右移轻环绕，露出左侧灯位与背景层次 |
| left | 左侧机位前推轻环绕，展示主灯/柔光箱/背景 |
| rear | 后侧机位纵深推进，展示动线与空间尺度 |

从 `scene_card` 注入：style_keywords、color_palette、color_temp、furniture、lighting_fixtures、product_category、room_size_band、forbidden。

**禁止**在 prompt 中要求出现具体品牌 logo 或屏幕文字。

---

## 6. 输出契约

```python
class PreviewVideoOutput(BaseModel):
    skill: Literal['preview_video']
    status: Literal['succeeded', 'failed']
    video_path: str | None
    source_image: str | None
    duration_sec: float
    resolution: str
    model: str
    sha256: str | None
    cost_cny: float
    warnings: list[str]
    error: str | None = None
```

产物路径：

```text
data/artifacts/{pipeline_run_id}/video/preview.mp4
data/artifacts/{pipeline_run_id}/video/meta.json
```

---

## 7. 降级与重试

| 场景 | 行为 |
|------|------|
| 1080P 失败 | 自动降 720P 重试一次 |
| 主模型失败 | 切备选模型一次 |
| 成本敏感模式 | 优先 flash 档（`VIDEO_TIER=flash`） |
| 无可用图 | failed |
| 超时 >300s | failed，可人工重试 |
| 文件损坏/0 字节 | 丢弃并重试 1 次 |

不自动重试业务校验失败（如 duration 超限）。

---

## 8. 成本与时延

| 档位 | 估算 | 时延 |
|------|------|------|
| flash 5s@720P | ~0.5–1.5 元 | 1–2 分钟 |
| standard 5–10s@720P | ~1–3 元 | 1–3 分钟 |
| 1080P 质量档 | ~3–8 元 | 2–4 分钟 |

默认：720P / 8s / standard。  
超时预算：≤300s。  
**必须异步 UI**（SSE 进度），禁止同步 HTTP 等待。

---

## 9. 幂等

- 同 `pipeline_run_id` 已有成功 mp4 → 复用
- 重试生成新 artifact，旧文件保留直至清理策略触发

---

## 10. 校验清单（运行时）

- [ ] 文件存在且大小 > 阈值（如 100KB）
- [ ] 可选：`ffprobe` 时长在 [duration_sec-1, duration_sec+2]
- [ ] 分辨率与请求一致或降级后一致
- [ ] sha256 写入 artifacts

---

## 11. 验收清单

- [ ] 基于真实 F3 首帧产出可播放 5–15s mp4
- [ ] 视觉与首帧场景连贯（人工抽检）
- [ ] 无声（或模型默认）符合产品预期
- [ ] 1080P 失败自动降 720P 成功
- [ ] 无图时 failed，不产生空文件
- [ ] mock DashScope 单测进 CI

---

## 12. 开放问题

1. 默认时长 5s 还是 8s？建议 8s（成本可接受，观感更好）。
2. 是否支持首尾帧（front→rear）插值？列为 P3 后实验项。
3. 是否允许用户重 roll 视频？建议付费或每日限额。
