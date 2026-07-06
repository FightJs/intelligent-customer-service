# 直播间视觉向量化智能客服 UI 原型

面向客户的 AI 对话式客服前端原型，采集直播间搭建需求的 11 节信息。

## 启动

```bash
npm install
npm run dev      # 启动开发服务器
npm test         # 跑单元测试
```

## 功能

- 左侧对话区：AI 按脚本提问，气泡内嵌选项卡/尺寸输入/图片上传
- 右侧仪表盘：11 节卡片网格，实时回显采集进度，点击就地展开编辑
- 顶部进度：环形完成度 + 重新开始
- 完成态：生成方案预览页（11 节摘要 + 占位交付物 + 原始 JSON）

## 技术栈

React 19 · TypeScript · Vite · Tailwind CSS · Vitest

## 范围说明

本原型不接后端 / 不接 LLM。AI 消息由 `src/data/scriptedFlow.ts` 本地脚本生成。后续可替换为真实 OpenAI Agents SDK 后端。

## 设计文档

见 `../docs/superpowers/specs/2026-07-06-livestream-cs-ui-design.md`。
