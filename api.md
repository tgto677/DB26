# 问卷系统 API 接口文档（V2）

> Base URL：`http://localhost:8000`
> 认证方式：JWT Bearer Token（除公开接口外，请求头需带 `Authorization: Bearer <token>`）
> 数据格式：JSON（`Content-Type: application/json`）
> 统一错误格式：`{"detail": "错误描述"}`（422 的 `detail` 为数组）
> 交互式文档：启动后端后访问 `http://localhost:8000/docs`
> 本版本文档覆盖 V1 全部接口 + V2 新增的题目库相关接口。

---

## 目录

1. [通用说明](#1-通用说明)
2. [认证接口](#2-认证接口)
3. [问卷接口](#3-问卷接口)
4. [回答与统计接口](#4-回答与统计接口)
5. [题目库接口（V2 新增）](#5-题目库接口v2-新增)
6. [数据结构](#6-数据结构)
7. [错误码](#7-错误码)
8. [附录：curl 示例](#8-附录curl-示例)

---

## 1. 通用说明

### 1.1 认证

登录/注册成功后返回 `access_token`，后续受保护接口在请求头携带：

```
Authorization: Bearer <access_token>
```

有效期由 `.env` 的 `ACCESS_TOKEN_EXPIRE_MINUTES` 控制（默认 1440 分钟）。

### 1.2 鉴权级别标记

| 标记     | 含义                                                         |
| -------- | ------------------------------------------------------------ |
| 🟢 公开   | 无需 token                                                   |
| 🟡 可选   | 带 token 会识别用户身份，不带也可访问（行为可能不同）        |
| 🔴 登录   | 必须带有效 token，否则 401                                   |
| 🔴 所有者 | 必须登录且是该资源的所有者（问卷创建者 / 题目库题目所有者），否则 403 |

### 1.3 ID 约定

- 问卷 `id`、用户 `id`、题目库题目 `id` 均为字符串形式的 MongoDB ObjectId。
- 接口返回的 `creator_id`、`user_id`、`owner_id`、`shared_from`、`copied_from` 统一为**字符串**。

### 1.4 时间格式

所有 `datetime` 字段为 UTC 的 ISO 8601 字符串，例如 `2026-10-20T08:00:00Z`。

---

## 2. 认证接口

### 2.1 注册

- **路径**：`POST /api/auth/register`
- **鉴权**：🟢 公开
- **说明**：创建用户并直接返回 token，注册即登录。

**请求体**

| 字段     | 类型   | 必填 | 约束                |
| -------- | ------ | ---- | ------------------- |
| username | string | 是   | 3~30 字符，全局唯一 |
| password | string | 是   | 6~128 字符          |

```json
{ "username": "alice", "password": "123456" }
```

**成功响应** `201`

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "user": {
    "id": "6701a2f3e4b0c1234567890a",
    "username": "alice",
    "created_at": "2026-10-22T08:00:00Z"
  }
}
```

**错误**：409 用户名已占用；422 参数校验失败。

---

### 2.2 登录（JSON）

- **路径**：`POST /api/auth/login`
- **鉴权**：🟢 公开

```json
{ "username": "alice", "password": "123456" }
```

**成功响应** `200`：同 2.1。**错误**：401 用户名或密码错误。

---

### 2.3 登录（表单，供 Swagger 使用）

- **路径**：`POST /api/auth/login/form`
- **鉴权**：🟢 公开
- **说明**：`application/x-www-form-urlencoded`，字段 `username`、`password`。仅用于 Swagger 的 Authorize 按钮，文档中隐藏。

---

### 2.4 获取当前用户

- **路径**：`GET /api/auth/me`
- **鉴权**：🔴 登录

**成功响应** `200`

```json
{
  "id": "6701a2f3e4b0c1234567890a",
  "username": "alice",
  "created_at": "2026-10-22T08:00:00Z"
}
```

**错误**：401 token 缺失/无效/过期，或用户不存在。

---

## 3. 问卷接口

### 3.1 创建问卷

- **路径**：`POST /api/surveys`
- **鉴权**：🔴 登录
- **说明**：`creator_id` 自动取当前用户。

**请求体**

| 字段            | 类型              | 必填 | 说明                          |
| --------------- | ----------------- | ---- | ----------------------------- |
| title           | string            | 是   | 1~200 字符                    |
| description     | string            | 否   | 默认空                        |
| allow_anonymous | bool              | 否   | 默认 `true`                   |
| allow_multiple  | bool              | 否   | 默认 `false`                  |
| questions       | array\<Question\> | 是   | 至少 1 题，题目 `id` 不能重复 |

**请求示例**

```json
{
  "title": "产品满意度调查",
  "description": "约 1 分钟完成",
  "allow_anonymous": true,
  "allow_multiple": false,
  "questions": [
    {
      "id": "q1",
      "type": "single",
      "title": "你对产品整体满意吗？",
      "required": true,
      "options": [
        { "label": "满意", "value": "yes" },
        { "label": "不满意", "value": "no" }
      ],
      "jump_rules": [
        { "option_value": "yes", "target_question_id": "q2" },
        { "option_value": "no", "target_question_id": null }
      ]
    },
    {
      "id": "q2",
      "type": "multiple",
      "title": "你喜欢哪些方面？",
      "required": false,
      "options": [
        { "label": "界面", "value": "ui" },
        { "label": "速度", "value": "speed" }
      ],
      "min_choices": 1,
      "max_choices": 2,
      "jump_rules": []
    }
  ]
}
```

> 题目结构见 [6.1](#61-question-题目)。若题目来自题目库，可带 `source_bank_id`（见 6.1）。

**成功响应** `201`：`Survey`（见 [6.2](#62-survey-问卷)）。

**错误**：401 未登录；422 字段校验失败。

---

### 3.2 我创建的问卷

- **路径**：`GET /api/surveys/mine`
- **鉴权**：🔴 登录
- **说明**：当前用户创建的所有问卷，按 `created_at` 倒序。

**成功响应** `200`：`Survey[]`

---

### 3.3 问卷详情

- **路径**：`GET /api/surveys/{survey_id}`
- **鉴权**：🟡 可选
- **说明**：
  - 匿名问卷任何人可访问；非匿名问卷仅创建者可访问。
  - 创建者访问时 `response_count` 为真实回答数，其他人恒为 0。

**成功响应** `200`：`Survey`

**错误**：400 id 非法；403 非匿名且非创建者；404 不存在。

---

### 3.4 复制问卷为新问卷（V2）

- **路径**：`POST /api/surveys/{survey_id}/duplicate`
- **鉴权**：🔴 所有者
- **说明**：复制题目与配置为新问卷，**不复制回答**；标题追加"（副本）"。用于"已发布问卷不可改，改题走复制"。

**成功响应** `201`：新 `Survey`

**错误**：401 未登录；403 非创建者；404 不存在。

---

## 4. 回答与统计接口

### 4.1 提交回答

- **路径**：`POST /api/surveys/{survey_id}/submit`
- **鉴权**：🟡 可选（是否必须登录由问卷 `allow_anonymous` 决定）
- **说明**：
  - 按 `jump_rules` 计算实际访问路径，只校验被访问到的题目。
  - 匿名提交 `user_id=null`，`is_anonymous=true`。
  - 只存实际被访问到的题目答案。

**请求体**

```json
{
  "answers": [
    { "question_id": "q1", "value": "no" },
    { "question_id": "q3", "value": "希望加载更快" },
    { "question_id": "q4", "value": 4 }
  ]
}
```

`value` 类型：single→string；multiple→string[]；text→string；number→number（可传数字字符串）。

**成功响应** `200`

```json
{ "message": "提交成功", "response_id": "6701b2f3e4b0c1234567890b" }
```

**错误**：400 校验失败/跳转循环；403 匿名或重复受限；404 不存在；409 重复提交。

---

### 4.2 问卷结果统计

- **路径**：`GET /api/surveys/{survey_id}/stats`
- **鉴权**：🔴 所有者
- **说明**：总体 + 逐题统计；逐题"回答人数"可能小于总回答数（因跳转）。

**成功响应** `200`：`SurveyStats`（见 [6.3](#63-surveystats-问卷统计)）

**错误**：401 未登录；403 非创建者；404 不存在。

---

## 5. 题目库接口（V2 新增）

> 所有题目库接口均需登录；除列表外，均校验 `owner_id`，非所有者 403。

### 5.1 保存题目

- **路径**：`POST /api/question-bank`
- **鉴权**：🔴 登录

**请求体**

| 字段     | 类型     | 必填 | 说明                                  |
| -------- | -------- | ---- | ------------------------------------- |
| question | Question | 是   | 题目结构，见 [6.1](#61-question-题目) |
| name     | string   | 否   | 库中显示名，默认取 `question.title`   |

**成功响应** `201`：`QuestionBankOut`（见 [6.4](#64-questionbankout-题目库题目)）

**错误**：401 未登录；422 题目结构非法。

---

### 5.2 我的题目库

- **路径**：`GET /api/question-bank`
- **鉴权**：🔴 登录
- **说明**：返回当前用户的全部题目（含自己保存、被分享、复制出的），按 `created_at` 倒序。

**成功响应** `200`：`QuestionBankOut[]`

---

### 5.3 删除题目

- **路径**：`DELETE /api/question-bank/{id}`
- **鉴权**：🔴 所有者

**成功响应** `204`（无返回体）

**错误**：400 id 非法；403 非所有者；404 不存在。

---

### 5.4 修改题目（记历史）

- **路径**：`PUT /api/question-bank/{id}`
- **鉴权**：🔴 所有者
- **说明**：修改前自动把旧版本写入历史；`current_version` 递增。

**请求体**

| 字段     | 类型     | 必填 | 说明                              |
| -------- | -------- | ---- | --------------------------------- |
| question | Question | 是   | 新题目结构                        |
| name     | string   | 否   | 新显示名，默认取 `question.title` |

**成功响应** `200`：更新后的 `QuestionBankOut`

**错误**：400 id 非法；403 非所有者；404 不存在；422 题目结构非法。

---

### 5.5 历史版本列表

- **路径**：`GET /api/question-bank/{id}/history`
- **鉴权**：🔴 所有者
- **说明**：按 `version` 倒序返回摘要。

**成功响应** `200`

```json
[
  {
    "version": 2,
    "action": "update",
    "name": "满意度题",
    "question_type": "single",
    "title": "你对产品整体满意吗？",
    "created_at": "2026-10-22T09:00:00Z"
  },
  {
    "version": 1,
    "action": "create",
    "name": "满意度题",
    "question_type": "single",
    "title": "你满意吗？",
    "created_at": "2026-10-22T08:00:00Z"
  }
]
```

`action` 取值：`create` / `update` / `restore`。

**错误**：400/403/404。

---

### 5.6 历史版本详情

- **路径**：`GET /api/question-bank/{id}/history/{version}`
- **鉴权**：🔴 所有者

**成功响应** `200`

```json
{
  "version": 1,
  "action": "create",
  "name": "满意度题",
  "question": { "id": "q1", "type": "single", "title": "你满意吗？", "required": true, "options": [], "jump_rules": [] },
  "created_at": "2026-10-22T08:00:00Z"
}
```

**错误**：400/403/404（版本不存在也 404）。

---

### 5.7 恢复历史版本

- **路径**：`POST /api/question-bank/{id}/restore/{version}`
- **鉴权**：🔴 所有者
- **说明**：把指定版本内容写回当前题目；恢复前把当前版本入历史（`action=restore`），恢复可再撤销。

**成功响应** `200`：恢复后的 `QuestionBankOut`

**错误**：400/403/404。

---

### 5.8 分享题目给其他用户

- **路径**：`POST /api/question-bank/{id}/share`
- **鉴权**：🔴 所有者
- **说明**：把题目**复制**一份到目标用户题目库，标记 `shared_from`。目标用户必须存在，不能分享给自己。

**请求体**

```json
{ "username": "bob" }
```

**成功响应** `201`：目标用户视角的 `QuestionBankOut`（`shared_from` 为分享者 id）

**错误**：400 分享给自己；403 非所有者；404 题目或目标用户不存在。

---

### 5.9 复制为新题目

- **路径**：`POST /api/question-bank/{id}/copy`
- **鉴权**：🔴 所有者
- **说明**：复制为一道新题目（同一所有者），原题与副本并存。副本 `current_version=1`，`copied_from` 指向原题。

**请求体**（可选，可传空体）

```json
{ "name": "满意度题-新版" }
```

不传 `name` 时默认"原名（副本）"。

**成功响应** `201`：新 `QuestionBankOut`

**错误**：400 id 非法；403 非所有者；404 不存在。

---

### 5.10 查看使用情况

- **路径**：`GET /api/question-bank/{id}/usages`
- **鉴权**：🔴 所有者
- **说明**：列出使用该题的问卷（当前用户创建且题目 `source_bank_id` 匹配）。同一问卷多次插入会产生多条（不同 `question_id`）。

**成功响应** `200`

```json
[
  {
    "survey_id": "6701a2f3e4b0c1234567890a",
    "survey_title": "满意度调查",
    "question_id": "q3",
    "created_at": "2026-10-20T08:00:00Z",
    "response_count": 10
  }
]
```

**错误**：400/403/404。

---

### 5.11 跨问卷题目统计

- **路径**：`GET /api/question-bank/{id}/stats`
- **鉴权**：🔴 所有者
- **说明**：跨所有使用该题的问卷聚合统计。按选项 `value` 合并（跨问卷 label 可能不同），以题目库当前 options 为基准，额外 value 追加。

**成功响应** `200`

```json
{
  "bank_id": "6701c2f3e4b0c1234567890c",
  "name": "满意度题",
  "question": { "id": "q1", "type": "single", "title": "你满意吗？", "required": true, "options": [], "jump_rules": [] },
  "survey_count": 2,
  "total_responses": 18,
  "answered": 15,
  "stat": {
    "type": "single",
    "options": [
      { "value": "yes", "label": "满意", "count": 10, "ratio": 0.6667 },
      { "value": "no", "label": "不满意", "count": 5, "ratio": 0.3333 }
    ]
  },
  "by_survey": [
    { "survey_id": "6701a2...", "survey_title": "满意度调查", "response_count": 10, "answered": 8 }
  ]
}
```

`stat` 按题型不同：

- single：`{ type, options }`
- multiple：`{ type, avg_selected, options }`
- text：`{ type, texts }`
- number：`{ type, min, max, avg, median, integer_count, non_integer_count }`

未被任何问卷使用时：`survey_count=0`、`total_responses=0`、`answered=0`、`stat` 为空结构（如 `options=[]` / `texts=[]` / 数字字段 `null`）。

**错误**：400/403/404。

---

## 6. 数据结构

### 6.1 Question（题目）

公共字段：

| 字段           | 类型           | 说明                                                         |
| -------------- | -------------- | ------------------------------------------------------------ |
| id             | string         | 题目唯一 id（问卷内唯一）                                    |
| type           | string         | `single` / `multiple` / `text` / `number`                    |
| title          | string         | 题目标题                                                     |
| required       | bool           | 是否必填，默认 `false`                                       |
| jump_rules     | JumpRule[]     | 跳转规则，默认 `[]`                                          |
| source_bank_id | string \| null | **V2**：来自题目库时记录其 id，否则为空。参与使用情况反查与跨问卷统计 |

#### single

```json
{
  "id": "q1", "type": "single", "title": "题目", "required": true,
  "options": [{ "label": "选项A", "value": "a" }],
  "jump_rules": [{ "option_value": "a", "target_question_id": "q3" }]
}
```

#### multiple

```json
{
  "id": "q2", "type": "multiple", "title": "题目", "required": false,
  "options": [{ "label": "A", "value": "a" }],
  "min_choices": 1, "max_choices": 3, "jump_rules": []
}
```

| 字段        | 类型        | 说明                                                         |
| ----------- | ----------- | ------------------------------------------------------------ |
| min_choices | int         | 最少选择数，默认 0                                           |
| max_choices | int \| null | 最多选择数，`null` 不限；不得小于 `min_choices`，不得大于选项数 |

#### text

```json
{
  "id": "q3", "type": "text", "title": "题目", "required": false,
  "min_length": 0, "max_length": 200, "jump_rules": []
}
```

#### number

```json
{
  "id": "q4", "type": "number", "title": "题目", "required": true,
  "min_value": 1, "max_value": 10, "integer_only": true, "jump_rules": []
}
```

#### JumpRule

```json
{ "option_value": "no", "target_question_id": "q3" }
```

`target_question_id` 为 `null` 表示结束问卷。从第 1 题按顺序遍历，命中即跳转。

#### QuestionOption

```json
{ "label": "满意", "value": "yes" }
```

---

### 6.2 Survey（问卷）

```json
{
  "id": "6701a2f3e4b0c1234567890a",
  "title": "产品满意度调查",
  "description": "约 1 分钟完成",
  "allow_anonymous": true,
  "allow_multiple": false,
  "questions": [ /* Question[] */ ],
  "creator_id": "6701a2f3e4b0c1234567890b",
  "created_at": "2026-10-20T08:00:00Z",
  "updated_at": "2026-10-20T08:00:00Z",
  "response_count": 10
}
```

| 字段           | 类型 | 说明                             |
| -------------- | ---- | -------------------------------- |
| response_count | int  | 回答数；非创建者查看详情时恒为 0 |

---

### 6.3 SurveyStats（问卷统计）

| 字段                                   | 类型                                                         | 说明              |
| -------------------------------------- | ------------------------------------------------------------ | ----------------- |
| total_responses                        | int                                                          | 总回答数          |
| anonymous_count                        | int                                                          | 匿名回答数        |
| logged_in_count                        | int                                                          | 登录回答数        |
| first_submitted_at / last_submitted_at | datetime \| null                                             | 最早/最晚提交时间 |
| questions                              | SingleStat[] \| MultipleStat[] \| TextStat[] \| NumberStat[] | 逐题统计          |

逐题统计字段与 V1 一致：

- **SingleStat**：`question_id, title, type, answered, options(OptionStat[])`
- **MultipleStat**：`question_id, title, type, answered, avg_selected, options(OptionStat[])`
- **TextStat**：`question_id, title, type, answered, texts`
- **NumberStat**：`question_id, title, type, answered, min, max, avg, median, integer_count, non_integer_count`
- **OptionStat**：`value, label, count, ratio`

---

### 6.4 QuestionBankOut（题目库题目）

```json
{
  "id": "6701c2f3e4b0c1234567890c",
  "owner_id": "6701a2f3e4b0c1234567890a",
  "question": { /* Question */ },
  "name": "满意度题",
  "current_version": 2,
  "copied_from": null,
  "shared_from": null,
  "shared_from_username": null,
  "shared_at": null,
  "created_at": "2026-10-22T08:00:00Z",
  "updated_at": "2026-10-22T09:00:00Z"
}
```

| 字段                 | 类型             | 说明                       |
| -------------------- | ---------------- | -------------------------- |
| id                   | string           | 题目库题目 id              |
| owner_id             | string           | 所有者用户 id              |
| question             | Question         | 题目内容                   |
| name                 | string           | 库中显示名                 |
| current_version      | int              | 当前版本号，从 1 开始      |
| copied_from          | string \| null   | 由哪道题复制而来（同用户） |
| shared_from          | string \| null   | 由哪个用户分享而来         |
| shared_from_username | string \| null   | 分享者用户名               |
| shared_at            | datetime \| null | 分享时间                   |

> `copied_from`（同用户派生）与 `shared_from`（跨用户分享）语义不同，前端分别标注"复制题"与"来自 xx"。

---

## 7. 错误码

| 状态码 | 含义         | 常见场景                                                     |
| ------ | ------------ | ------------------------------------------------------------ |
| 200    | 成功         |                                                              |
| 201    | 创建成功     | 注册、创建问卷、保存题目、分享、复制                         |
| 204    | 删除成功     | 删除题目，无返回体                                           |
| 400    | 请求错误     | id 非法；回答校验失败；跳转循环；分享给自己                  |
| 401    | 未认证       | token 缺失/无效/过期；用户名或密码错误                       |
| 403    | 无权限       | 非所有者操作题目/看统计；非匿名问卷非创建者访问；匿名提交受限 |
| 404    | 资源不存在   | 问卷/题目/目标用户/历史版本不存在                            |
| 409    | 冲突         | 用户名已存在；重复提交                                       |
| 422    | 参数校验失败 | 请求体字段类型/约束不符（`detail` 为数组）                   |

**401 响应示例**

```json
{ "detail": "无效或过期的凭证" }
```

**422 响应示例**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body", "questions", 0],
      "msg": "Value error, max_choices 不能小于 min_choices",
      "input": { "...": "..." }
    }
  ]
}
```

---

## 8. 附录：curl 示例

**注册并保存 token**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"123456"}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

**创建问卷**

```bash
curl -X POST http://localhost:8000/api/surveys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "title": "测试问卷",
    "allow_anonymous": true,
    "allow_multiple": false,
    "questions": [{
      "id": "q1", "type": "single", "title": "满意吗？", "required": true,
      "options": [{"label":"满意","value":"yes"},{"label":"不满意","value":"no"}],
      "jump_rules": []
    }]
  }'
```

**匿名提交**

```bash
curl -X POST http://localhost:8000/api/surveys/<survey_id>/submit \
  -H "Content-Type: application/json" \
  -d '{"answers":[{"question_id":"q1","value":"yes"}]}'
```

**查看问卷统计（创建者）**

```bash
curl http://localhost:8000/api/surveys/<survey_id>/stats \
  -H "Authorization: Bearer $TOKEN"
```

**保存题目到题目库**

```bash
curl -X POST http://localhost:8000/api/question-bank \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "question": {
      "id": "q1", "type": "single", "title": "满意吗？", "required": true,
      "options": [{"label":"满意","value":"yes"},{"label":"不满意","value":"no"}],
      "jump_rules": []
    },
    "name": "满意度题"
  }'
```

**修改题目**

```bash
curl -X PUT http://localhost:8000/api/question-bank/<id> \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "question": {
      "id": "q1", "type": "single", "title": "新标题", "required": true,
      "options": [{"label":"A","value":"a"}], "jump_rules": []
    },
    "name": "改名"
  }'
```

**查看历史 / 某版本 / 恢复**

```bash
curl http://localhost:8000/api/question-bank/<id>/history -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/api/question-bank/<id>/history/1 -H "Authorization: Bearer $TOKEN"
curl -X POST http://localhost:8000/api/question-bank/<id>/restore/1 -H "Authorization: Bearer $TOKEN"
```

**分享题目**

```bash
curl -X POST http://localhost:8000/api/question-bank/<id>/share \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"username":"bob"}'
```

**复制为新题目**

```bash
curl -X POST http://localhost:8000/api/question-bank/<id>/copy \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"满意度题-新版"}'
```

**查看使用情况 / 跨问卷统计**

```bash
curl http://localhost:8000/api/question-bank/<id>/usages -H "Authorization: Bearer $TOKEN"
curl http://localhost:8000/api/question-bank/<id>/stats -H "Authorization: Bearer $TOKEN"
```