"""
FastAPI 应用主入口
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path

from app.api.routes import router
from app.config import BASE_DIR

# 创建 FastAPI 应用
app = FastAPI(
    title="公文自动排版工具",
    description="基于大模型的党政机关公文自动排版API服务",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS（允许前端跨域访问）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册 API 路由
app.include_router(router, prefix="/api", tags=["公文排版"])

# 挂载静态文件目录
static_dir = BASE_DIR / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """根路由，返回欢迎信息"""
    return {
        "message": "欢迎使用公文自动排版工具",
        "docs": "/docs",
        "api": "/api"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
