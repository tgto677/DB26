"""
生成测试数据：
    python seed_test_data.py

依赖：与后端相同（pymongo / passlib / bcrypt / python-dotenv）。
会先清空 users / surveys / responses 三个集合，再写入测试数据。
"""
from datetime import datetime, timedelta, timezone
import random

from bson import ObjectId

from app.auth import hash_password
from app.database import users_collection, surveys_collection, responses_collection, init_db


PASSWORD = "123456"


def now():
    return datetime.now(timezone.utc)


def seed_users():
    users = [
        {"username": "alice", "password": PASSWORD},
        {"username": "bob", "password": PASSWORD},
        {"username": "carol", "password": PASSWORD},
        {"username": "dave", "password": PASSWORD},
    ]
    docs = []
    base_time = now() - timedelta(days=10)
    for i, u in enumerate(users):
        docs.append({
            "username": u["username"],
            "password_hash": hash_password(u["password"]),
            "created_at": base_time + timedelta(hours=i),
        })
    users_collection.insert_many(docs)
    return {d["username"]: d for d in docs}


def seed_surveys(users):
    alice = str(users["alice"]["_id"])
    bob = str(users["bob"]["_id"])
    carol = str(users["carol"]["_id"])
    t0 = now() - timedelta(days=7)

    surveys = []

    # 1. 产品满意度调查（alice）：单选跳转 + 多选限选 + 文本 + 数字
    surveys.append({
        "creator_id": alice,
        "title": "产品满意度调查",
        "description": "感谢参与，约 1 分钟完成。",
        "allow_anonymous": True,
        "allow_multiple": False,
        "created_at": t0,
        "updated_at": t0,
        "questions": [
            {
                "id": "q1", "type": "single", "title": "你对产品整体满意吗？", "required": True,
                "options": [
                    {"label": "满意", "value": "yes"},
                    {"label": "一般", "value": "mid"},
                    {"label": "不满意", "value": "no"},
                ],
                "jump_rules": [
                    {"option_value": "no", "target_question_id": "q3"},
                    {"option_value": "yes", "target_question_id": "q2"},
                ],
            },
            {
                "id": "q2", "type": "multiple", "title": "你喜欢哪些方面？", "required": False,
                "options": [
                    {"label": "界面", "value": "ui"},
                    {"label": "速度", "value": "speed"},
                    {"label": "功能", "value": "feature"},
                    {"label": "价格", "value": "price"},
                ],
                "min_choices": 1, "max_choices": 2,
                "jump_rules": [],
            },
            {
                "id": "q3", "type": "text", "title": "请说说你的建议", "required": False,
                "min_length": 0, "max_length": 200,
                "jump_rules": [],
            },
            {
                "id": "q4", "type": "number", "title": "你愿意给产品打几分（1-10）？", "required": True,
                "min_value": 1, "max_value": 10, "integer_only": True,
                "jump_rules": [],
            },
        ],
    })

    # 2. 用户反馈（bob）：匿名 + 可多次 + 文本必填
    surveys.append({
        "creator_id": bob,
        "title": "用户反馈收集",
        "description": "匿名反馈，欢迎多次提交。",
        "allow_anonymous": True,
        "allow_multiple": True,
        "created_at": t0 + timedelta(days=1),
        "updated_at": t0 + timedelta(days=1),
        "questions": [
            {
                "id": "f1", "type": "text", "title": "你的反馈内容", "required": True,
                "min_length": 5, "max_length": 500,
                "jump_rules": [],
            },
            {
                "id": "f2", "type": "number", "title": "你的年龄（可选）", "required": False,
                "min_value": 0, "max_value": 120, "integer_only": True,
                "jump_rules": [],
            },
        ],
    })

    # 3. 内部活动报名（carol）：不允许匿名 + 不可重复 + 单选多选
    surveys.append({
        "creator_id": carol,
        "title": "内部团建活动报名",
        "description": "需要登录后填写，每人限一次。",
        "allow_anonymous": False,
        "allow_multiple": False,
        "created_at": t0 + timedelta(days=2),
        "updated_at": t0 + timedelta(days=2),
        "questions": [
            {
                "id": "a1", "type": "single", "title": "是否参加本次团建？", "required": True,
                "options": [
                    {"label": "参加", "value": "join"},
                    {"label": "不参加", "value": "skip"},
                ],
                "jump_rules": [
                    {"option_value": "skip", "target_question_id": None},
                    {"option_value": "join", "target_question_id": "a2"},
                ],
            },
            {
                "id": "a2", "type": "multiple", "title": "你倾向于哪些活动？", "required": True,
                "options": [
                    {"label": "聚餐", "value": "dinner"},
                    {"label": "爬山", "value": "hiking"},
                    {"label": "桌游", "value": "boardgame"},
                    {"label": "KTV", "value": "ktv"},
                ],
                "min_choices": 1, "max_choices": 3,
                "jump_rules": [],
            },
            {
                "id": "a3", "type": "text", "title": "其他建议", "required": False,
                "min_length": 0, "max_length": 100,
                "jump_rules": [],
            },
        ],
    })

    # 4. 满意度快问（alice）：极简单选，允许匿名、可多次
    surveys.append({
        "creator_id": alice,
        "title": "满意度快问",
        "description": "一题，10 秒完成。",
        "allow_anonymous": True,
        "allow_multiple": True,
        "created_at": t0 + timedelta(days=3),
        "updated_at": t0 + timedelta(days=3),
        "questions": [
            {
                "id": "s1", "type": "single", "title": "今天心情如何？", "required": True,
                "options": [
                    {"label": "😄 很好", "value": "great"},
                    {"label": "🙂 还行", "value": "ok"},
                    {"label": "😞 不好", "value": "bad"},
                ],
                "jump_rules": [],
            },
        ],
    })

    # 5. 数字填空测试（bob）：范围 + 非整数
    surveys.append({
        "creator_id": bob,
        "title": "价格敏感度调查",
        "description": "测试数字填空范围与小数。",
        "allow_anonymous": True,
        "allow_multiple": True,
        "created_at": t0 + timedelta(days=4),
        "updated_at": t0 + timedelta(days=4),
        "questions": [
            {
                "id": "p1", "type": "number", "title": "你能接受的最高单价（0-999.99）", "required": True,
                "min_value": 0, "max_value": 999.99, "integer_only": False,
                "jump_rules": [],
            },
            {
                "id": "p2", "type": "single", "title": "是否愿意推荐给朋友？", "required": True,
                "options": [
                    {"label": "愿意", "value": "yes"},
                    {"label": "不愿意", "value": "no"},
                ],
                "jump_rules": [],
            },
        ],
    })

    result = surveys_collection.insert_many(surveys)
    ids = result.inserted_ids
    return [
        {"_id": ids[i], **surveys[i]} for i in range(len(surveys))
    ]


def seed_responses(users, surveys):
    """为问卷插入一些回答。"""
    alice = users["alice"]["_id"]
    bob = users["bob"]["_id"]
    carol = users["carol"]["_id"]
    dave = users["dave"]["_id"]
    t = now() - timedelta(days=3)

    docs = []

    s1 = surveys[0]  # 产品满意度（alice）
    # 登录用户回答（yes -> q2 -> 跳过 q3 -> q4）
    docs.append({
        "survey_id": s1["_id"], "user_id": bob, "is_anonymous": False,
        "answers": [
            {"question_id": "q1", "value": "yes"},
            {"question_id": "q2", "value": ["ui", "speed"]},
            {"question_id": "q4", "value": 8},
        ],
        "submitted_at": t + timedelta(hours=1),
    })
    # 匿名回答（no -> 跳到 q3 -> q4）
    docs.append({
        "survey_id": s1["_id"], "user_id": None, "is_anonymous": True,
        "answers": [
            {"question_id": "q1", "value": "no"},
            {"question_id": "q3", "value": "希望加载更快一些"},
            {"question_id": "q4", "value": 4},
        ],
        "submitted_at": t + timedelta(hours=2),
    })
    # 登录回答（mid -> 无跳转命中 -> q2 -> q3 -> q4）
    docs.append({
        "survey_id": s1["_id"], "user_id": carol, "is_anonymous": False,
        "answers": [
            {"question_id": "q1", "value": "mid"},
            {"question_id": "q2", "value": ["feature"]},
            {"question_id": "q3", "value": "整体不错"},
            {"question_id": "q4", "value": 7},
        ],
        "submitted_at": t + timedelta(hours=3),
    })
    # 匿名（yes -> q2 -> q4）
    docs.append({
        "survey_id": s1["_id"], "user_id": None, "is_anonymous": True,
        "answers": [
            {"question_id": "q1", "value": "yes"},
            {"question_id": "q2", "value": ["price"]},
            {"question_id": "q4", "value": 9},
        ],
        "submitted_at": t + timedelta(hours=4),
    })

    s2 = surveys[1]  # 用户反馈（bob，可多次匿名）
    feedback_texts = [
        "希望增加导出功能", "界面可以更简洁一些", "整体体验不错，继续加油",
        "手机端适配需要优化", "加载速度有点慢",
    ]
    for i, txt in enumerate(feedback_texts):
        docs.append({
            "survey_id": s2["_id"],
            "user_id": bob if i % 2 == 0 else None,
            "is_anonymous": i % 2 != 0,
            "answers": [
                {"question_id": "f1", "value": txt},
                *([{"question_id": "f2", "value": random.randint(18, 60)}] if i % 3 == 0 else []),
            ],
            "submitted_at": t + timedelta(hours=5 + i),
        })

    s3 = surveys[2]  # 内部报名（carol，不匿名、不可重复）
    docs.append({
        "survey_id": s3["_id"], "user_id": alice, "is_anonymous": False,
        "answers": [
            {"question_id": "a1", "value": "join"},
            {"question_id": "a2", "value": ["dinner", "hiking"]},
            {"question_id": "a3", "value": "尽量安排在周末"},
        ],
        "submitted_at": t + timedelta(hours=10),
    })
    docs.append({
        "survey_id": s3["_id"], "user_id": bob, "is_anonymous": False,
        "answers": [
            {"question_id": "a1", "value": "join"},
            {"question_id": "a2", "value": ["boardgame"]},
        ],
        "submitted_at": t + timedelta(hours=11),
    })
    # skip -> 结束，只有 a1
    docs.append({
        "survey_id": s3["_id"], "user_id": dave, "is_anonymous": False,
        "answers": [
            {"question_id": "a1", "value": "skip"},
        ],
        "submitted_at": t + timedelta(hours=12),
    })

    s4 = surveys[3]  # 满意度快问（alice，可多次匿名）
    moods = ["great", "ok", "great", "bad", "ok", "great"]
    for i, m in enumerate(moods):
        anon = i % 2 == 0
        docs.append({
            "survey_id": s4["_id"],
            "user_id": None if anon else (alice if i % 3 == 0 else bob),
            "is_anonymous": anon,
            "answers": [{"question_id": "s1", "value": m}],
            "submitted_at": t + timedelta(hours=13 + i),
        })

    s5 = surveys[4]  # 价格敏感度（bob）
    prices = [99.9, 150.0, 200.5, 88.0, 300.0]
    for i, p in enumerate(prices):
        docs.append({
            "survey_id": s5["_id"],
            "user_id": None if i % 2 == 0 else alice,
            "is_anonymous": i % 2 == 0,
            "answers": [
                {"question_id": "p1", "value": p},
                {"question_id": "p2", "value": "yes" if p <= 200 else "no"},
            ],
            "submitted_at": t + timedelta(hours=20 + i),
        })

    responses_collection.insert_many(docs)


def main():
    print("初始化索引…")
    init_db()

    print("清空旧数据…")
    users_collection.delete_many({})
    surveys_collection.delete_many({})
    responses_collection.delete_many({})

    print("写入用户…")
    users = seed_users()
    print(f"  {len(users)} 个用户，密码均为 {PASSWORD}")

    print("写入问卷…")
    surveys = seed_surveys(users)
    print(f"  {len(surveys)} 份问卷")

    print("写入回答…")
    seed_responses(users, surveys)
    total = responses_collection.count_documents({})
    print(f"  {total} 条回答")

    print("\n完成。可用账号登录：")
    for name in users:
        print(f"  {name} / {PASSWORD}")


if __name__ == "__main__":
    main()