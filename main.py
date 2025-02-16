from contextlib import asynccontextmanager

from fastapi import FastAPI

from routes import user_router, question_router, management_router
from storage.mysql import executors


@asynccontextmanager
async def lifespan(_: FastAPI):
    await executors.initialize()  # 创建数据库连接
    yield
    await executors.destroy()  # 销毁数据库连接


app = FastAPI(title="SmartOJ-后端接口文档", lifespan=lifespan)

app.include_router(user_router, prefix="/user", tags=["用户"])
app.include_router(question_router, prefix="/question", tags=["题目"])
app.include_router(management_router, prefix="/management", tags=["后台管理"])
