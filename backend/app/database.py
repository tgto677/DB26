from pymongo import MongoClient, ASCENDING
from pymongo.database import Database

from .config import settings

# 全局 MongoClient（应用生命周期内复用）
client: MongoClient = MongoClient(settings.MONGO_URI)

db: Database = client[settings.MONGO_DB_NAME]

# 集合
users_collection = db["users"]
surveys_collection = db["surveys"]
responses_collection = db["responses"]
question_bank_collection = db["question_bank"]


def init_db() -> None:
    """初始化索引。应用启动时调用。"""
    # 用户名唯一
    users_collection.create_index([("username", ASCENDING)], unique=True)

    # 问卷按创建者查询
    surveys_collection.create_index([("creator_id", ASCENDING)])
    surveys_collection.create_index([("created_at", ASCENDING)])

    # 回答按问卷查询
    responses_collection.create_index([("survey_id", ASCENDING)])
    responses_collection.create_index([("submitted_at", ASCENDING)])

    question_bank_collection.create_index([("owner_id", ASCENDING)])
    question_bank_collection.create_index([("created_at", ASCENDING)])

def close_db() -> None:
    """关闭连接。应用关闭时调用。"""
    client.close()