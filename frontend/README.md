# 直播间视觉向量化智能客服 UI 原型

面向客户的 AI 对话式客服前端原型，采集直播间搭建需求的 11 节信息。

## 启动

```bash
npm install
npm run dev      # 启动开发服务器
npm test         # 跑单元测试
```

## 功能

- **左栏 · 采集进度**：11 节垂直列表，状态色点（灰未采集/蓝进行中/绿完成），当前节高亮，只读
- **中栏 · 对话采集**：AI 按脚本提问，气泡内嵌选项卡/尺寸输入/图片上传；多选·尺寸·图片支持累积后点"确认"再推进
- **右栏 · 交付物 + 订单**（采集完成后从右侧滑入）：
  - 方案概要：客户/品类/面积/预算/交付时间
  - 4 个交付物占位：场景设计/设备清单/效果图/评分报告
  - 订单表单：客户名/电话预填，套餐下拉，总价自动，发送订单（UI 模拟，不调后端）
- **顶部 TopBar**：环形完成度 + `X/47 已采集` + 重新开始

## 技术栈

React 19 · TypeScript · Vite · Tailwind CSS · Vitest

## 范围说明

本原型不接后端 / 不接 LLM。AI 消息由 `src/data/scriptedFlow.ts` 本地脚本生成。后续可替换为真实 OpenAI Agents SDK 后端。

## 设计文档

- 原始 2 栏设计：`../docs/superpowers/specs/2026-07-06-livestream-cs-ui-design.md`
- 三栏重构：`../docs/superpowers/specs/2026-07-06-three-column-layout-design.md`
