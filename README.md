# 在线问卷系统 V2 — README

> 本版本在 V1（问卷创建/填写/统计）基础上，围绕**题目复用与治理**做了功能更新。启动方式与 V1 兼容。

---

## 一、V2 功能更新（相对 V1）

V1 已具备：用户注册登录、问卷创建（单选/多选/文本/数字、必填、数量/长度/范围约束、条件跳转、匿名与多次填写控制）、URL 发放填写、创建者结果统计。

V2 新增以下能力：

### 1. 题目库（保存与复用）

- 创建问卷时，可把某道题**存入"我的题目库"**。
- 新增独立页面**题目库**（`/question-bank.html`），查看、编辑、删除已保存的题目。
- 创建问卷时可通过**"从题目库添加"**插入已保存题目（插入时自动重新生成题目 id、清空跳转规则）。

### 2. 分享题目给其他用户

- 题目库中的题可**分享给指定用户名**。
- 分享采用**复制式**：对方题目库中出现一份独立副本，标注"来自 xx"。
- 副本归接收者所有，可独立修改/删除，不影响分享者原题。

### 3. 修改题目 + 历史版本 + 恢复

- 题目库中的题可**编辑**（标题、题型、选项、必填、数量/长度/范围/整数等）。
- 每次修改前自动保存旧版本到历史，**可查看历史版本列表与某版本完整内容**。
- 可**恢复**到任意历史版本；恢复本身也记一条历史，支持再撤销。

### 4. 复制为新题目（多版本并存）

- 可把某道题**复制为新题目**，原题与副本同时存在。
- 副本独立演进（有自己的版本历史），可单独插入问卷。
- 副本标注"复制题"，与跨用户分享的"来自 xx"区分。

### 5. 查看使用情况与跨问卷统计

- 可查看某道题**被哪些问卷使用**（问卷标题、创建时间、回答数、题号）。
- 可**跨问卷聚合该题的统计结果**：按选项 value 合并计数与占比，文本合并原文，数字输出最小值/最大值/平均值/中位数，并列出各问卷贡献。
- 关联方式：从题目库插入题目时，问卷题目会记录 `source_bank_id`，用于反查与统计。

> V1 已有问卷与题目库旧数据在 V2 下保持兼容：缺少新字段时读取端按默认值处理，无需数据迁移。

---

## 二、项目启动方式

### 环境要求

- Python 3.10+
- MongoDB（本地默认 `mongodb://localhost:27017`）
- Node.js（用于 `npx serve`）

### 1. 启动 MongoDB

确保 MongoDB 已运行。

### 2. 配置并启动后端

```bash
cd backend
```

`.env`：

```env
MONGO_URI=mongodb://localhost:27017
MONGO_DB_NAME=survey_db
JWT_SECRET=change-me-to-a-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440
```

安装依赖并启动：

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- 健康检查：`http://localhost:8000/api/health`
- 接口文档：`http://localhost:8000/docs`

> `requirements.txt` 中已锁定 `bcrypt==4.0.1`，以兼容 `passlib 1.7.4` 与 Python 3.10。

### 3. 启动前端

```bash
cd frontend
npx serve -l 5000 -c serve.json
```

> 必须带 `-c serve.json`（其中含 `/survey/{id}`、`/survey-detail/{id}` 的 rewrites 配置），且**不要加 `-s`**。

访问：`http://localhost:5000/`

### 4. （可选）写入测试数据

```bash
cd backend
python seed_test_data.py
```

会清空 `users` / `surveys` / `responses` 三个集合并写入测试用户、问卷与回答（**仅测试环境使用**）。

> 新增的 `question_bank`、`question_bank_history` 集合无需手动初始化，首次写入时自动创建，索引在后端启动时由 `init_db()` 建立。

### 5. 若历史数据 ID 类型不一致

```bash
cd backend
python fix_ids.py
```

---

## 三、页面与路由

| 路径                  | 页面                  | 说明                                        |
| --------------------- | --------------------- | ------------------------------------------- |
| `/`                   | 入口                  | 未登录自动弹登录框，已登录跳个人主页        |
| `/home.html`          | 个人主页              | 我创建的问卷                                |
| `/create.html`        | 创建问卷              | 题目构建器，含"存入题目库""从题目库添加"    |
| `/question-bank.html` | **题目库（V2 新增）** | 查看/编辑/复制/分享/历史/恢复/使用情况/统计 |
| `/survey/{id}`        | 填写问卷              | 问卷分享链接                                |
| `/survey-detail/{id}` | 问卷详情 + 统计       | 仅创建者，需登录                            |

---

## 四、数据集合

| 集合                    | 说明                                    |
| ----------------------- | --------------------------------------- |
| `users`                 | 用户                                    |
| `surveys`               | 问卷（题目结构含可选 `source_bank_id`） |
| `responses`             | 回答                                    |
| `question_bank`         | **V2 新增**：题目库                     |
| `question_bank_history` | **V2 新增**：题目库版本历史             |

---

## 五、注意事项

1. **已发布问卷的题目不可原地修改**；如需改题，可通过"复制为新题目/复制问卷"派生后在新对象中修改。
2. **分享与复制均为独立副本**：删除原题不影响副本，修改副本不影响原题。
3. **跨问卷统计按选项 value 聚合**：若某问卷中该题选项被改过，额外 value 会以自身为标签追加展示，回答不丢失。
4. **权限**：题目库的增删改查、分享、历史、恢复、使用情况与统计均按 `owner_id` 隔离，非所有者返回 403。
5. **`seed_test_data.py` 会清空三个集合**，请勿在生产库运行。

---

## 六、V2 新增接口一览

| 方法   | 路径                                        | 说明               |
| ------ | ------------------------------------------- | ------------------ |
| POST   | `/api/question-bank`                        | 保存题目           |
| GET    | `/api/question-bank`                        | 我的题目库         |
| DELETE | `/api/question-bank/{id}`                   | 删除题目           |
| PUT    | `/api/question-bank/{id}`                   | 修改题目（记历史） |
| GET    | `/api/question-bank/{id}/history`           | 历史列表           |
| GET    | `/api/question-bank/{id}/history/{version}` | 历史版本详情       |
| POST   | `/api/question-bank/{id}/restore/{version}` | 恢复旧版本         |
| POST   | `/api/question-bank/{id}/share`             | 分享给其他用户     |
| POST   | `/api/question-bank/{id}/copy`              | 复制为新题目       |
| GET    | `/api/question-bank/{id}/usages`            | 被哪些问卷使用     |
| GET    | `/api/question-bank/{id}/stats`             | 跨问卷题目统计     |
