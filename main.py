from contextlib import asynccontextmanager

from fastapi import FastAPI

from routes import user_router, question_router, management_router
from storage.mysql import executors
from mq.broker import broker
from utils.openapi.docs import custom_swagger_ui_html


@asynccontextmanager
async def lifespan(_: FastAPI):
    await executors.initialize()  # 创建数据库连接
    await broker.startup()  # 启动消息队列服务
    yield
    await executors.destroy()  # 销毁数据库连接
    await broker.shutdown()  # 关闭消息队列服务


app = FastAPI(title='智能算法刷题平台-后端 API 文档', docs_url=None, lifespan=lifespan)


@app.get('/docs', include_in_schema=False)
def custom_swagger_ui_html_endpoint():
    return custom_swagger_ui_html(
        openapi_url="/openapi.json",
        title="智能算法刷题平台-后端 API 文档",
        swagger_ui_parameters={"persistAuthorization": True, 'withCredentials': True}
    )


app.include_router(user_router, prefix="/user", tags=["用户"])
app.include_router(question_router, prefix="/question", tags=["题目"])
app.include_router(management_router, prefix="/management", tags=["后台管理"])
