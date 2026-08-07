# 管理后台用户与交付物接口 Spec

> 用于前后端联调。接口实现：`backend/api/app.py`；数据结构与级联删除：`backend/store/db.py`。
>
> Base URL：`http://localhost:8000/api`（生产环境替换为实际 API 地址）

## 1. 通用约定

### 1.1 鉴权

除注册、登录外，所有接口都需要 JWT：

```http
Authorization: Bearer <token>
```

本 spec 中 `/admin/*` 接口要求当前登录用户 `role === "admin"`。普通用户访问返回 `403`，不会执行任何读写操作。

### 1.2 错误格式

业务错误统一为 FastAPI 默认 JSON：

```json
{"detail": "错误说明"}
```

常见状态码：

| 状态码 | 含义 |
| --- | --- |
| `401` | 缺少、无效或过期 token；前端应清理登录态并跳转登录页 |
| `403` | 已登录但不是管理员 |
| `404` | 目标用户/交付物不存在 |
| `409` | 用户名冲突，或触发管理员保护规则 |
| `422` | 请求 JSON 不符合 Pydantic 类型/枚举约束 |

日期字段均为 UTC ISO 8601 字符串，例如 `2026-08-07T08:30:00+00:00`。

## 2. 用户管理接口

### 2.1 用户列表

```http
GET /api/admin/users
Authorization: Bearer <admin-token>
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `search` | string | 无 | 按 `username` 模糊匹配；不传表示全部 |
| `sort_by` | `id \| username \| created_at` | `id` | 非白名单值回退为 `id` |
| `order` | `asc \| desc` | `asc` | 其他值按 `asc` 处理 |
| `page` | integer | `1` | 小于 1 时按 1 处理 |
| `size` | integer | `20` | 小于 1 时按 1 处理 |

响应 `200`：

```json
{
  "items": [
    {
      "id": 1,
      "username": "admin",
      "role": "admin",
      "created_at": "2026-08-07T08:30:00+00:00"
    }
  ],
  "total": 1,
  "admin_count": 1,
  "page": 1,
  "size": 20
}
```

`admin_count` 是数据库中管理员总数，不受 `search`、`page`、`size` 影响；列表项本身不含 `delivery_count`。

### 2.2 创建用户

```http
POST /api/admin/users
Authorization: Bearer <admin-token>
Content-Type: application/json
```

请求：

```json
{
  "username": "operator01",
  "password": "pass123456",
  "role": "user"
}
```

字段：

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| `username` | string | 是 | 服务端会 trim；trim 后至少 2 个字符，必须唯一 |
| `password` | string | 是 | 至少 6 个字符；服务端只保存 hash |
| `role` | `user \| admin` | 否 | 默认 `user` |

响应 `201` 为用户安全详情（不返回 `password_hash`）：

```json
{
  "id": 12,
  "username": "operator01",
  "role": "user",
  "created_at": "2026-08-07T08:35:00+00:00",
  "delivery_count": 0
}
```

失败：`400` 用户名/密码过短；`409` 用户名已存在。

### 2.3 用户详情

```http
GET /api/admin/users/{user_id}
Authorization: Bearer <admin-token>
```

响应 `200`：

```json
{
  "id": 12,
  "username": "operator01",
  "role": "user",
  "created_at": "2026-08-07T08:35:00+00:00",
  "delivery_count": 2
}
```

`delivery_count` 为该用户当前拥有的交付物数量。不存在返回 `404`。

### 2.4 修改用户

```http
PATCH /api/admin/users/{user_id}
Authorization: Bearer <admin-token>
Content-Type: application/json
```

请求示例（支持部分更新）：

```json
{
  "username": "operator-renamed",
  "password": "newpass123",
  "role": "admin"
}
```

可更新字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `username` | string 或 null | 字段出现时不能为空；trim 后至少 2 个字符且唯一 |
| `password` | string 或 null | 字段出现时不能为空且至少 6 个字符；用于重置密码 |
| `role` | `user/admin` 或 null | 字段出现时不可为 null |

至少提交一个字段，否则 `400`。成功响应 `200` 返回更新后的用户安全详情（含最新 `delivery_count`，不含密码 hash）。用户名冲突返回 `409`，用户不存在返回 `404`。

### 2.5 删除用户

```http
DELETE /api/admin/users/{user_id}
Authorization: Bearer <admin-token>
```

成功响应：`204 No Content`，响应体为空。

删除在同一事务中清理：

1. 用户所有会话 `sessions`；
2. 这些会话下的消息 `messages`；
3. 用户所有交付物 `deliveries`；
4. 用户记录本身。

保护规则：

| 场景 | 状态码 | detail |
| --- | --- | --- |
| 用户不存在 | `404` | `用户不存在` |
| 删除当前登录管理员自己 | `409` | `不能删除当前登录的管理员` |
| 删除系统最后一个管理员 | `409` | `不能删除系统最后一个管理员` |

## 3. 交付物管理接口

> 交付物记录由用户调用 `POST /api/generate/markdown` 后产生；管理端只管理已落库的 Markdown 交付物。

### 3.1 交付物列表

```http
GET /api/admin/deliverables
Authorization: Bearer <admin-token>
```

查询参数：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `user_id` | integer | 无 | 按归属用户精确筛选 |
| `search` | string | 无 | 按客户名 `customer_name` 或用户名 `owner_username` 模糊匹配 |
| `sort_by` | `id \| customer_name \| created_at` | `id` | 非白名单值回退为 `id` |
| `order` | `asc \| desc` | `desc` | 默认最新记录优先 |
| `page` | integer | `1` | 小于 1 时按 1 处理 |
| `size` | integer | `20` | 小于 1 时按 1 处理 |

响应 `200`（列表不返回 Markdown 正文）：

```json
{
  "items": [
    {
      "id": 33,
      "session_id": "a1b2c3d4e5f6",
      "user_id": 12,
      "customer_name": "云裳",
      "created_at": "2026-08-07T09:00:00+00:00",
      "owner_username": "operator01"
    }
  ],
  "total": 1,
  "page": 1,
  "size": 20
}
```

### 3.2 交付物详情

```http
GET /api/admin/deliverables/{delivery_id}
Authorization: Bearer <admin-token>
```

响应 `200` 在列表字段基础上增加 `markdown`：

```json
{
  "id": 33,
  "session_id": "a1b2c3d4e5f6",
  "user_id": 12,
  "customer_name": "云裳",
  "markdown": "# 直播间搭建方案\n...",
  "created_at": "2026-08-07T09:00:00+00:00",
  "owner_username": "operator01"
}
```

不存在返回 `404`，`detail` 为 `交付物不存在`。

### 3.3 修改交付物

```http
PATCH /api/admin/deliverables/{delivery_id}
Authorization: Bearer <admin-token>
Content-Type: application/json
```

请求示例：

```json
{
  "customer_name": "云裳旗舰店",
  "markdown": "# 更新后的方案\n..."
}
```

字段均为可选，至少一个字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `customer_name` | string 或 null | trim 后保存；空字符串会保存为 `null`，可用于清空客户名 |
| `markdown` | string 或 null | 字段出现时去除首尾空白后不能为空；保存原始 Markdown 文本 |

成功响应 `200` 返回完整交付物详情（包含更新后的 `markdown`）。空 JSON 返回 `400`（`至少需要提供一个修改字段`），Markdown 为空返回 `400`，不存在返回 `404`。

### 3.4 删除交付物

```http
DELETE /api/admin/deliverables/{delivery_id}
Authorization: Bearer <admin-token>
```

成功响应：`204 No Content`。只删除指定交付物，不影响所属用户、会话或消息；不存在返回 `404`。

## 4. 前端联调落地清单

1. 管理端请求统一带 `Authorization: Bearer <token>`；接口返回 `401` 时清理本地认证状态。
2. 用户列表类型需要包含 `admin_count`（当前前端 `Paged<T>` 类型未声明该字段）。
3. 用户列表行不要依赖 `delivery_count`；打开详情或创建/修改成功后使用响应中的 `delivery_count` 更新详情视图。
4. 创建用户使用 `POST`，修改使用 `PATCH`；修改密码时只提交明文 `password`，不要在前端保存或展示 hash。
5. 删除用户成功后清理当前列表/详情缓存；由于后端已级联清理会话、消息、交付物，不需要前端逐条补删。
6. 删除/降级操作对 `409` 应直接展示后端 `detail`，特别是“当前登录管理员”和“最后一个管理员”保护提示。
7. 交付物列表用于表格，详情接口用于预览 Markdown；编辑后用 `PATCH` 刷新详情，删除成功后从列表移除并更新总数。
8. `search`、筛选、排序或分页变化时重新请求列表，并以响应中的 `total/page/size` 为分页依据。

## 5. 与当前前端 client 的差异

当前 `frontend/src/api/client.ts` 已实现用户/交付物列表与交付物详情读取，但尚未覆盖本 spec 的：

- `admin_count` 类型声明；
- 用户创建、详情、修改、删除方法；
- 交付物修改、删除方法；
- 业务错误 `detail` 的统一解析（当前部分 admin 方法仅抛出状态码）。

联调接入时按本 spec 补齐类型和方法即可，不应把 mock 用户字段（如 `email`、`status`、`last_login`）发送给后端；这些字段不属于当前后端用户模型。
