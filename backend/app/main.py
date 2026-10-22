from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import init_db, close_db
from .routes import auth_routes, survey_routes, response_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    print("✅ MongoDB 连接成功，索引已初始化")
    yield
    close_db()
    print("🔌 MongoDB 连接已关闭")


app = FastAPI(
    title="Survey System API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5000",
        "http://127.0.0.1:5000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_routes.router)
app.include_router(survey_routes.router)
app.include_router(response_routes.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}