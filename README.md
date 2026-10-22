# 问卷系统 API 接口文档

> Base URL：`http://localhost:8000`
> 认证方式：JWT Bearer Token（除公开接口外，请求头需带 `Authorization: Bearer <token>`）
> 数据格式：JSON（`Content-Type: application/json`）
> 统一错误格式：`{"detail": "错误描述"}`

---

## 目录

1. [通用说明](#1-通用说明)
2. [认证接口](#2-认证接口)
3. [问卷接口](#3-问卷接口)
4. [回答与统计接口](#4-回答与统计接口)
5. [数据结构](#5-数据结构)
6. [错误码](#6-错误码)

---

## 1. 通用说明

### 1.1 认证

登录/注册成功后返回 `access_token`，后续受保护接口在请求头携带：

```
Authorization: Bearer <access_token>
```

Token 有效期由 `.env` 的 `ACCESS_TOKEN_EXPIRE_MINUTES` 控制（默认 1440 分钟）。

### 1.2 鉴权级别标记

本文档用以下标记说明接口鉴权要求：

| 标记     | 含义                                              |
| -------- | ------------------------------------------------- |
| 🟢 公开   | 无需 token                                        |
| 🟡 可选   | 带 token 会识别用户身份，不带也可访问（行为不同） |
| 🔴 登录   | 必须带有效 token，否则 401                        |
| 🔴 创建者 | 必须登录且是该问卷的创建者，否则 403              |

### 1.3 ID 约定

- 问卷 `id`、用户 `id` 均为字符串形式的 MongoDB ObjectId。
- `creator_id`、`user_id` 在接口返回中统一为**字符串**。

---

## 2. 认证接口

### 2.1 注册

- **路径**：`POST /api/auth/register`
- **鉴权**：🟢 公开
- **说明**：创建用户并直接返回 token。

**请求体**

| 字段     | 类型   | 必填 | 约束                |
| -------- | ------ | ---- | ------------------- |
| username | string | 是   | 3~30 字符，全局唯一 |
| password | string | 是   | 6~128 字符          |

```json
{
  "username": "alice",
  "password": "123456"
}
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

**错误**

| 状态码 | 场景           |
| ------ | -------------- |
| 409    | 用户名已被占用 |
| 422    | 参数校验失败   |

---

### 2.2 登录（JSON）

- **路径**：`POST /api/auth/login`
- **鉴权**：🟢 公开

**请求体**

```json
{
  "username": "alice",
  "password": "123456"
}
```

**成功响应** `200`

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

**错误**

| 状态码 | 场景             |
| ------ | ---------------- |
| 401    | 用户名或密码错误 |

---

### 2.3 登录（表单，供 Swagger 使用）

- **路径**：`POST /api/auth/login/form`
- **鉴权**：🟢 公开
- **说明**：`application/x-www-form-urlencoded`，字段 `username`、`password`。仅用于 Swagger 的 Authorize 按钮，前端不调用，文档中隐藏。

**成功响应** `200`：同 2.2

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

**错误**

| 状态码 | 场景                               |
| ------ | ---------------------------------- |
| 401    | token 缺失/无效/过期，或用户不存在 |

---

## 3. 问卷接口

### 3.1 创建问卷

- **路径**：`POST /api/surveys`
- **鉴权**：🔴 登录
- **说明**：创建一份问卷，`creator_id` 自动取当前用户。

**请求体**

| 字段            | 类型              | 必填 | 说明                     |
| --------------- | ----------------- | ---- | ------------------------ |
| title           | string            | 是   | 1~200 字符               |
| description     | string            | 否   | 默认空                   |
| allow_anonymous | bool              | 否   | 默认 `true`              |
| allow_multiple  | bool              | 否   | 默认 `false`             |
| questions       | array\<Question\> | 是   | 至少 1 题，`id` 不能重复 |

**Question 结构**（见 [5.1](#51-question-题目)），按 `type` 区分：

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
        { "label": "速度", "value": "speed" },
        { "label": "功能", "value": "feature" }
      ],
      "min_choices": 1,
      "max_choices": 2,
      "jump_rules": []
    },
    {
      "id": "q3",
      "type": "text",
      "title": "你的建议",
      "required": false,
      "min_length": 0,
      "max_length": 200,
      "jump_rules": []
    },
    {
      "id": "q4",
      "type": "number",
      "title": "打分（1-10 整数）",
      "required": true,
      "min_value": 1,
      "max_value": 10,
      "integer_only": true,
      "jump_rules": []
    }
  ]
}
```

**成功响应** `201`：返回 `Survey` 对象（见 [5.2](#52-survey-问卷)）。

**错误**

| 状态码 | 场景                                                         |
| ------ | ------------------------------------------------------------ |
| 401    | 未登录                                                       |
| 422    | 字段校验失败（如题目 id 重复、`max_choices < min_choices`、跳转目标不存在、数字范围非法等） |

---

### 3.2 我创建的问卷

- **路径**：`GET /api/surveys/mine`
- **鉴权**：🔴 登录
- **说明**：返回当前用户创建的所有问卷，按 `created_at` 倒序。

**成功响应** `200`：`Survey[]`

---

### 3.3 问卷列表（公开）

- **路径**：`GET /api/surveys`
- **鉴权**：🟢 公开
- **说明**：返回所有问卷，按 `created_at` 倒序，附 `response_count`（回答数）。

**成功响应** `200`：`Survey[]`

---

### 3.4 问卷详情

- **路径**：`GET /api/surveys/{survey_id}`
- **鉴权**：🟡 可选
- **说明**：
  - 匿名问卷（`allow_anonymous=true`）：任何人可访问。
  - 非匿名问卷（`allow_anonymous=false`）：仅创建者可访问，其他人 403。
  - 创建者访问时 `response_count` 为真实回答数，其他人恒为 0。

**路径参数**

| 参数      | 类型   | 说明          |
| --------- | ------ | ------------- |
| survey_id | string | 问卷 ObjectId |

**成功响应** `200`：`Survey`

**错误**

| 状态码 | 场景                                         |
| ------ | -------------------------------------------- |
| 400    | survey_id 格式非法                           |
| 403    | 非匿名问卷，且当前用户不是创建者（含未登录） |
| 404    | 问卷不存在                                   |

---

## 4. 回答与统计接口

### 4.1 提交回答

- **路径**：`POST /api/surveys/{survey_id}/submit`
- **鉴权**：🟡 可选（是否必须登录由问卷 `allow_anonymous` 决定）
- **说明**：
  - 服务端按 `jump_rules` 计算实际访问路径，**只校验被访问到的题目**，被跳过的必填题不报错。
  - 匿名字段 `user_id` 为 `null`，`is_anonymous=true`。
  - 校验：必填、选项合法性、多选数量、文本长度、数字范围/整数。

**请求体**

| 字段    | 类型                | 说明                        |
| ------- | ------------------- | --------------------------- |
| answers | array\<AnswerItem\> | `{question_id, value}` 列表 |

`value` 按题型：

| 题型     | value 类型                           |
| -------- | ------------------------------------ |
| single   | string（选项 value）                 |
| multiple | string[]（选项 value 数组）          |
| text     | string                               |
| number   | number（可传数字字符串，服务端转换） |

```json
{
  "answers": [
    { "question_id": "q1", "value": "no" },
    { "question_id": "q3", "value": "希望加载更快" },
    { "question_id": "q4", "value": 4 }
  ]
}
```

**成功响应** `200`

```json
{
  "message": "提交成功",
  "response_id": "6701b2f3e4b0c1234567890b"
}
```

**错误**

| 状态码 | 场景                                                 |
| ------ | ---------------------------------------------------- |
| 400    | 必填未答、选项非法、数量/长度/范围越界、跳转规则循环 |
| 403    | 问卷不允许匿名但未登录；或不允许重复但未登录         |
| 404    | 问卷不存在                                           |
| 409    | 不允许重复提交，且当前用户已提交过                   |

---

### 4.2 问卷结果统计

- **路径**：`GET /api/surveys/{survey_id}/stats`
- **鉴权**：🔴 创建者
- **说明**：返回总体统计 + 逐题统计。逐题统计的"回答人数"可能小于总回答数（因跳转跳过）。

**成功响应** `200`：`SurveyStats`（见 [5.3](#53-surveystats-统计)）

```json
{
  "survey_id": "6701a2f3e4b0c1234567890a",
  "title": "产品满意度调查",
  "total_responses": 10,
  "anonymous_count": 4,
  "logged_in_count": 6,
  "first_submitted_at": "2026-10-20T08:00:00Z",
  "last_submitted_at": "2026-10-22T09:30:00Z",
  "questions": [
    {
      "question_id": "q1",
      "title": "你对产品整体满意吗？",
      "type": "single",
      "answered": 10,
      "options": [
        { "value": "yes", "label": "满意", "count": 7, "ratio": 0.7 },
        { "value": "no", "label": "不满意", "count": 3, "ratio": 0.3 }
      ]
    },
    {
      "question_id": "q2",
      "title": "你喜欢哪些方面？",
      "type": "multiple",
      "answered": 3,
      "avg_selected": 1.67,
      "options": [
        { "value": "ui", "label": "界面", "count": 2, "ratio": 0.6667 },
        { "value": "speed", "label": "速度", "count": 1, "ratio": 0.3333 },
        { "value": "feature", "label": "功能", "count": 2, "ratio": 0.6667 }
      ]
    },
    {
      "question_id": "q3",
      "title": "你的建议",
      "type": "text",
      "answered": 4,
      "texts": ["希望加载更快", "整体不错"]
    },
    {
      "question_id": "q4",
      "title": "打分（1-10 整数）",
      "type": "number",
      "answered": 10,
      "min": 4,
      "max": 10,
      "avg": 7.2,
      "median": 7,
      "integer_count": 10,
      "non_integer_count": 0
    }
  ]
}
```

**错误**

| 状态码 | 场景                     |
| ------ | ------------------------ |
| 401    | 未登录                   |
| 403    | 当前用户不是该问卷创建者 |
| 404    | 问卷不存在               |

---

## 5. 数据结构

### 5.1 Question（题目）

按 `type` 分为四种，公共字段：

| 字段       | 类型       | 说明                                      |
| ---------- | ---------- | ----------------------------------------- |
| id         | string     | 题目唯一 id（问卷内唯一）                 |
| type       | string     | `single` / `multiple` / `text` / `number` |
| title      | string     | 题目标题                                  |
| required   | bool       | 是否必填，默认 `false`                    |
| jump_rules | JumpRule[] | 跳转规则，默认 `[]`                       |

#### single（单选）

```json
{
  "id": "q1",
  "type": "single",
  "title": "题目",
  "required": true,
  "options": [{ "label": "选项A", "value": "a" }],
  "jump_rules": [{ "option_value": "a", "target_question_id": "q3" }]
}
```

| 字段    | 类型             | 说明                        |
| ------- | ---------------- | --------------------------- |
| options | QuestionOption[] | 至少 1 个，`value` 题内唯一 |

#### multiple（多选）

```json
{
  "id": "q2",
  "type": "multiple",
  "title": "题目",
  "required": false,
  "options": [{ "label": "A", "value": "a" }],
  "min_choices": 1,
  "max_choices": 3,
  "jump_rules": []
}
```

| 字段        | 类型             | 说明                                                         |
| ----------- | ---------------- | ------------------------------------------------------------ |
| options     | QuestionOption[] | 至少 1 个                                                    |
| min_choices | int              | 最少选择数，默认 0                                           |
| max_choices | int \| null      | 最多选择数，`null` 不限；不得小于 `min_choices`，不得大于选项数 |

#### text（文本填空）

```json
{
  "id": "q3",
  "type": "text",
  "title": "题目",
  "required": false,
  "min_length": 0,
  "max_length": 200,
  "jump_rules": []
}
```

| 字段       | 类型        | 说明                                         |
| ---------- | ----------- | -------------------------------------------- |
| min_length | int         | 最少字数，默认 0                             |
| max_length | int \| null | 最多字数，`null` 不限；不得小于 `min_length` |

#### number（数字填空）

```json
{
  "id": "q4",
  "type": "number",
  "title": "题目",
  "required": true,
  "min_value": 1,
  "max_value": 10,
  "integer_only": true,
  "jump_rules": []
}
```

| 字段         | 类型           | 说明                                      |
| ------------ | -------------- | ----------------------------------------- |
| min_value    | number \| null | 最小值，`null` 不限                       |
| max_value    | number \| null | 最大值，`null` 不限；不得小于 `min_value` |
| integer_only | bool           | 是否仅允许整数，默认 `false`              |

#### JumpRule（跳转规则）

```json
{ "option_value": "no", "target_question_id": "q3" }
```

| 字段               | 类型           | 说明                                                       |
| ------------------ | -------------- | ---------------------------------------------------------- |
| option_value       | string         | 触发值：单选/多选按选项 `value` 匹配（多选为"包含即触发"） |
| target_question_id | string \| null | 跳转目标题 id；`null` 表示结束问卷                         |

**执行规则**：按题目顺序遍历，对每道已访问的题按 `jump_rules` 顺序匹配，命中即跳转；未命中则进入下一题。

---

### 5.2 Survey（问卷）

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

| 字段            | 类型       | 说明                             |
| --------------- | ---------- | -------------------------------- |
| id              | string     | 问卷 id                          |
| title           | string     | 标题                             |
| description     | string     | 描述                             |
| allow_anonymous | bool       | 是否允许匿名填写                 |
| allow_multiple  | bool       | 是否允许同一人多次填写           |
| questions       | Question[] | 题目列表                         |
| creator_id      | string     | 创建者用户 id                    |
| created_at      | datetime   | 创建时间（UTC）                  |
| updated_at      | datetime   | 更新时间（UTC）                  |
| response_count  | int        | 回答数；非创建者查看详情时恒为 0 |

---

### 5.3 SurveyStats（统计）

```json
{
  "survey_id": "string",
  "title": "string",
  "total_responses": 10,
  "anonymous_count": 4,
  "logged_in_count": 6,
  "first_submitted_at": "datetime | null",
  "last_submitted_at": "datetime | null",
  "questions": [ /* 见下 */ ]
}
```

#### SingleStat

| 字段        | 类型         | 说明                 |
| ----------- | ------------ | -------------------- |
| question_id | string       |                      |
| title       | string       |                      |
| type        | `"single"`   |                      |
| answered    | int          | 回答该题人数         |
| options     | OptionStat[] | 每个选项的计数与占比 |

#### MultipleStat

| 字段         | 类型         | 说明                                      |
| ------------ | ------------ | ----------------------------------------- |
| question_id  | string       |                                           |
| title        | string       |                                           |
| type         | `"multiple"` |                                           |
| answered     | int          | 回答该题人数                              |
| avg_selected | float        | 人均选择项数                              |
| options      | OptionStat[] | 每个选项被选次数与占比（分母 = answered） |

#### TextStat

| 字段        | 类型     | 说明                 |
| ----------- | -------- | -------------------- |
| question_id | string   |                      |
| title       | string   |                      |
| type        | `"text"` |                      |
| answered    | int      |                      |
| texts       | string[] | 全部非空文本回答原文 |

#### NumberStat

| 字段              | 类型           | 说明            |
| ----------------- | -------------- | --------------- |
| question_id       | string         |                 |
| title             | string         |                 |
| type              | `"number"`     |                 |
| answered          | int            |                 |
| min / max         | number \| null | 最小值 / 最大值 |
| avg / median      | number \| null | 平均值 / 中位数 |
| integer_count     | int            | 整数回答数      |
| non_integer_count | int            | 非整数回答数    |

#### OptionStat

| 字段  | 类型   | 说明                   |
| ----- | ------ | ---------------------- |
| value | string | 选项值                 |
| label | string | 选项文字               |
| count | int    | 被选次数               |
| ratio | float  | 占比（0~1，保留 4 位） |

---

## 6. 错误码

| 状态码 | 含义         | 常见场景                                                     |
| ------ | ------------ | ------------------------------------------------------------ |
| 200    | 成功         |                                                              |
| 201    | 创建成功     | 注册、创建问卷                                               |
| 400    | 请求错误     | 问卷 id 格式非法；回答校验失败；跳转循环                     |
| 401    | 未认证       | token 缺失/无效/过期；用户名或密码错误                       |
| 403    | 无权限       | 非创建者看统计；非匿名问卷非创建者访问；匿名提交受限         |
| 404    | 资源不存在   | 问卷不存在                                                   |
| 409    | 冲突         | 用户名已存在；重复提交                                       |
| 422    | 参数校验失败 | 请求体字段类型/约束不符（FastAPI/Pydantic 自动返回，`detail` 为数组） |

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

## 附录：快速示例（curl）

**注册并保存 token**

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"123456"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
```

**创建问卷**

```bash
curl -X POST http://localhost:8000/api/surveys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"title":"测试问卷","allow_anonymous":true,"allow_multiple":false,"questions":[{"id":"q1","type":"single","title":"满意吗？","required":true,"options":[{"label":"满意","value":"yes"},{"label":"不满意","value":"no"}],"jump_rules":[]}]}'
```

**匿名提交**

```bash
curl -X POST http://localhost:8000/api/surveys/<survey_id>/submit \
  -H "Content-Type: application/json" \
  -d '{"answers":[{"question_id":"q1","value":"yes"}]}'
```

**查看统计（创建者）**

```bash
curl http://localhost:8000/api/surveys/<survey_id>/stats \
  -H "Authorization: Bearer $TOKEN"
```