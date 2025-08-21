from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from uvicorn.config import logger

import settings
from routes import user_router, question_router, management_router, codesandbox_router
from storage.mysql import engine
from storage.cache import close_cache_connections
from mq.broker import broker
from utils.openapi.docs import custom_swagger_ui_html


async def on_startup():
    logger.info("Creating RabbitMQ connection")
    await broker.startup()


async def on_shutdown():
    logger.info("Disconnecting with MySQL")
    await engine.dispose()
    logger.info("Disconnecting with RabbitMQ")
    await broker.shutdown()
    logger.info("Disconnecting with Redis")
    await close_cache_connections()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await on_startup()
    yield
    await on_shutdown()


app = FastAPI(title='智能算法刷题平台-后端 API 文档', docs_url=None, lifespan=lifespan)


@app.get('/docs', include_in_schema=False)
def custom_swagger_ui_html_endpoint():
    return custom_swagger_ui_html(
        openapi_url="/openapi.json",
        title="智能算法刷题平台-后端 API 文档",
        swagger_ui_parameters={"persistAuthorization": True, 'withCredentials': True},
        swagger_css_url="/static/css/swagger/swagger-ui.css",
        swagger_js_url="/static/js/swagger/swagger-ui-bundle.js"
    )


app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(user_router, prefix="/user", tags=["用户信息相关接口"])
app.include_router(question_router, prefix="/question")
app.include_router(management_router, prefix="/management", tags=["后台管理系统相关接口"])
app.include_router(codesandbox_router, prefix="/codesandbox", tags=["代码沙箱接口"])


if __name__ == "__main__":
    run_config = {
        "host": "127.0.0.1" if settings.DEV_ENV else "0.0.0.0",
        "log_config": "log-config.json"
    }
    uvicorn.run(app, **run_config)
