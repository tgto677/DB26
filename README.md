# 在线问卷系统（Online Survey System）

一个基于 **FastAPI + MongoDB + 原生 HTML/JS** 的轻量级在线问卷系统。支持四种题型、条件跳转、匿名与重复填写控制，并提供结果统计。

---

## ✨ 功能特性

- **用户认证**：注册 / 登录，JWT 鉴权，密码 bcrypt 哈希存储
- **问卷管理**：创建问卷（仅登录用户），公开浏览，创建者查看统计
- **四种题型**
  - 单选（single）
  - 多选（multiple，可限制最少/最多选择数量）
  - 文本填空（text，可限制字数）
  - 数字填空（number，可限制范围、是否仅整数）
- **必填 / 非必填**：每题可独立设置
- **条件跳转**：根据选项跳转到指定题目或直接结束问卷
- **填写控制**：问卷可设置是否允许匿名填写、是否允许同一人多次填写
- **结果统计**：
  - 总体：总回答数、匿名/登录数、时间范围
  - 单选/多选：每项计数与占比，多选人均选择数
  - 文本：全部回答原文
  - 数字：最小值/最大值/平均值/中位数、整数占比
- **前后端一致的跳转引擎**：前端实时计算路径，后端提交时复核

---

## 🧱 技术栈

| 层           | 技术                                                 |
| ------------ | ---------------------------------------------------- |
| 后端框架     | FastAPI 0.115                                        |
| 数据库驱动   | pymongo 4.8                                          |
| 数据库       | MongoDB                                              |
| 数据校验     | Pydantic 2.9                                         |
| 认证         | python-jose（JWT）+ passlib[bcrypt]（bcrypt==4.0.1） |
| 配置         | python-dotenv                                        |
| 前端         | 原生 HTML + CSS + JavaScript（fetch）                |
| 前端静态服务 | `npx serve`（端口 5000）                             |

> 适配 Python 3.10。`bcrypt` 必须锁定在 `4.0.1`，否则与 `passlib 1.7.4` 不兼容。

---

## 📁 项目结构

```
survey-system/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── config.py                # 读取 .env 配置
│   │   ├── database.py              # MongoClient、集合、索引初始化
│   │   ├── auth.py                  # 密码哈希、JWT、鉴权依赖
│   │   ├── schemas.py               # Pydantic 模型（用户/题目/问卷/提交/统计）
│   │   ├── main.py                  # FastAPI 入口、CORS、路由注册
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── auth_routes.py       # 注册 / 登录 / me
│   │   │   ├── survey_routes.py     # 创建 / 我的 / 列表 / 详情
│   │   │   └── response_routes.py   # 提交回答 / 结果统计
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── survey_service.py    # 问卷业务逻辑
│   │       ├── response_service.py  # 提交校验 + 跳转引擎
│   │       └── stats_service.py     # 统计聚合
│   ├── seed_test_data.py            # 生成测试数据
│   ├── fix_ids.py                   # ID 类型迁移脚本
│   ├── requirements.txt
│   └── .env
│
└── frontend/
    ├── index.html                   # 重定向到 survey.html
    ├── survey.html                  # 问卷广场 + 填写弹窗
    ├── home.html                    # 个人主页（我创建的问卷）
    ├── create.html                  # 创建问卷（题目构建器）
    ├── survey-detail.html           # 问卷详情 + 统计
    ├── css/
    │   └── style.css
    └── js/
        ├── api.js                   # API 封装、token 存取
        ├── common.js                # 导航栏、登录注册弹窗、登录守卫
        └── fill.js                  # 填写弹窗 + 前端跳转引擎
```

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- MongoDB（本地默认 `mongodb://localhost:27017`）
- Node.js（用于 `npx serve`）

### 1. 启动 MongoDB

确保 MongoDB 已运行，默认监听 `27017`。

### 2. 配置后端

```bash
cd backend
cp .env .env.bak   # 如已有 .env 可跳过
```

`.env` 内容：

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=survey_db
JWT_SECRET=change-me-to-a-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

> **重要**：生产环境务必把 `JWT_SECRET` 换成随机字符串。

### 3. 安装依赖并启动后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- 健康检查：`http://localhost:8000/api/health`
- 接口文档（Swagger）：`http://localhost:8000/docs`

### 4. 启动前端

```bash
cd frontend
npx serve -l 5000
```

访问：`http://localhost:5000/survey.html`

### 5. （可选）写入测试数据

```bash
cd backend
python seed_test_data.py
```

会清空 `users` / `surveys` / `responses` 三个集合并写入：

- **4 个用户**（密码均为 `123456`）：`alice`、`bob`、`carol`、`dave`
- **5 份问卷**，覆盖四种题型、跳转、匿名/多次等场景
- **约 24 条回答**，用于统计页演示

> 若历史数据 ID 类型不一致（ObjectId 与字符串混用），运行：
> ```bash
> python fix_ids.py
> ```

---

## 🖥️ 使用流程

1. **注册 / 登录**：打开 `survey.html`，点击右上角「登录 / 注册」。
2. **创建问卷**：登录后进入「创建问卷」页，添加题目、配置选项/校验/跳转，保存发布。
3. **填写问卷**：在「问卷广场」选择问卷填写；支持跳转、逐题校验。
4. **查看统计**：在「个人主页」点击「查看详情」进入统计页（仅创建者可看）。
5. **退出登录**：右上角「退出」。

---

## 🔌 API 概览

| 方法 | 路径                       | 鉴权   | 说明             |
| ---- | -------------------------- | ------ | ---------------- |
| POST | `/api/auth/register`       | 公开   | 注册并返回 token |
| POST | `/api/auth/login`          | 公开   | JSON 登录        |
| GET  | `/api/auth/me`             | 登录   | 当前用户信息     |
| POST | `/api/surveys`             | 登录   | 创建问卷         |
| GET  | `/api/surveys/mine`        | 登录   | 我创建的问卷     |
| GET  | `/api/surveys`             | 公开   | 问卷列表         |
| GET  | `/api/surveys/{id}`        | 可选   | 问卷详情         |
| POST | `/api/surveys/{id}/submit` | 可选   | 提交回答         |
| GET  | `/api/surveys/{id}/stats`  | 创建者 | 结果统计         |

### 快速示例

```bash
# 注册
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"123456"}'

# 登录
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"123456"}'

# 创建问卷（带 token）
curl -X POST http://localhost:8000/api/surveys \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "title": "满意度调查",
    "allow_anonymous": true,
    "allow_multiple": false,
    "questions": [{
      "id": "q1", "type": "single", "title": "满意吗？",
      "required": true,
      "options": [{"label":"满意","value":"yes"},{"label":"不满意","value":"no"}],
      "jump_rules": []
    }]
  }'

# 匿名提交
curl -X POST http://localhost:8000/api/surveys/<survey_id>/submit \
  -H "Content-Type: application/json" \
  -d '{"answers":[{"question_id":"q1","value":"yes"}]}'

# 查看统计（创建者）
curl http://localhost:8000/api/surveys/<survey_id>/stats \
  -H "Authorization: Bearer <token>"
```

---

## 🗄️ 数据模型

### users

```json
{
  "_id": "ObjectId",
  "username": "alice",
  "password_hash": "bcrypt hash",
  "created_at": "ISODate"
}
```

索引：`username`（唯一）。

### surveys

```json
{
  "_id": "ObjectId",
  "creator_id": "字符串 user id",
  "title": "标题",
  "description": "描述",
  "allow_anonymous": true,
  "allow_multiple": false,
  "questions": [ /* 题目数组 */ ],
  "created_at": "ISODate",
  "updated_at": "ISODate"
}
```

索引：`creator_id`、`created_at`。

**题目结构**（按 `type` 区分）：

```json
// 单选
{ "id": "q1", "type": "single", "title": "...", "required": true,
  "options": [{"label":"满意","value":"yes"}],
  "jump_rules": [{"option_value":"no","target_question_id":"q3"}] }

// 多选
{ "id": "q2", "type": "multiple", "title": "...", "required": false,
  "options": [...], "min_choices": 1, "max_choices": 2, "jump_rules": [] }

// 文本
{ "id": "q3", "type": "text", "title": "...", "required": false,
  "min_length": 0, "max_length": 200, "jump_rules": [] }

// 数字
{ "id": "q4", "type": "number", "title": "...", "required": true,
  "min_value": 1, "max_value": 10, "integer_only": true, "jump_rules": [] }
```

**跳转规则**：`target_question_id` 为 `null` 表示结束问卷；按顺序匹配，命中即跳。

### responses

```json
{
  "_id": "ObjectId",
  "survey_id": "ObjectId",
  "user_id": "字符串 user id | null",
  "is_anonymous": false,
  "answers": [
    { "question_id": "q1", "value": "yes" },
    { "question_id": "q2", "value": ["ui", "speed"] },
    { "question_id": "q4", "value": 8 }
  ],
  "submitted_at": "ISODate"
}
```

索引：`survey_id`、`submitted_at`。

> 只存实际被访问到的题目；被跳转跳过的不写入，因此统计中"该题回答人数"可能小于总回答数。

---

## ✅ 校验设计

校验分四层：

1. **Pydantic 结构校验**（创建时）：题目 id 唯一、跳转目标存在、多选数量关系、文本/数字范围关系 → 422
2. **业务规则校验**：用户名唯一、问卷存在、权限（创建者/匿名访问）、匿名与重复提交约束 → 403/404/409
3. **提交时按路径校验**：先算跳转路径，只校验被访问到的题；各题型按选项/数量/长度/范围校验 → 400
4. **前端即时校验**：逐题校验，提升体验；后端始终复核

---

## ⚠️ 常见问题

### 1. `bcrypt` 与 `passlib` 不兼容

确保 `bcrypt==4.0.1`（已在 `requirements.txt` 中锁定）。验证：

```bash
python -c "import bcrypt; print(bcrypt.__version__)"
```

### 2. 启动种子数据报 `E11000 duplicate key ... email_1`

`users` 集合存在遗留的唯一索引 `email_1`。删除它：

```javascript
// mongosh
use survey_db
db.users.dropIndex("email_1")
```

`seed_test_data.py` 已内置清理逻辑。

### 3. 登录后个人主页为空 / 非匿名问卷打不开

通常是 `creator_id` / `user_id` 的 ObjectId 与字符串类型不一致。运行迁移：

```bash
cd backend
python fix_ids.py
```

### 4. 前端跨域失败

后端 CORS 已允许 `http://localhost:5000` 与 `http://127.0.0.1:5000`。若前端用其他端口，请修改 `backend/app/main.py` 的 `allow_origins`。

### 5. 前端请求后端地址

默认在 `frontend/js/api.js` 顶部：

```javascript
const API_BASE = "http://localhost:8000";
```

如需修改后端地址，改这里即可。
