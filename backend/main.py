import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 必须在任何 Paddle 相关导入之前设置这些环境变量
os.environ['FLAGS_enable_pir_api'] = '0'
os.environ['FLAGS_enable_onednn'] = '0'
os.environ['FLAGS_use_mkldnn'] = '0'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True'

# vLLM 多进程设置 - 必须在导入其他模块前设置
os.environ['VLLM_WORKER_MULTIPROC_METHOD'] = 'spawn'

import logging
import multiprocessing

# 设置多进程启动方式为 spawn（vLLM 要求）
try:
    multiprocessing.set_start_method('spawn', force=True)
except RuntimeError:
    pass  # 已经设置过

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import init_db, SessionLocal, Auditor
from backend.api.upload import router as upload_router
from backend.api.audit import router as audit_router
from backend.api.user import router as user_router
from backend.services.auth_service import get_auth_service
from backend.logger_config import logger

logging.getLogger("uvicorn").handlers = []
logging.getLogger("uvicorn.access").handlers = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在启动财务审核系统...")
    init_db()
    logger.info("数据库初始化完成")
    
    # 初始化默认审核人账号
    db = SessionLocal()
    try:
        auth_service = get_auth_service()
        auth_service.init_default_auditor(db)
    finally:
        db.close()
    
    logger.info("系统启动完成")
    yield
    logger.info("正在关闭财务审核系统...")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload_router, prefix=settings.API_PREFIX)
app.include_router(audit_router, prefix=settings.API_PREFIX)
app.include_router(user_router, prefix=settings.API_PREFIX)


@app.get("/")
def root():
    logger.info("Root endpoint accessed")
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "status": "running"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 禁用热重载以避免开发时不必要的重启
        log_config=None
    )
