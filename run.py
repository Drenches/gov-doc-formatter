#!/usr/bin/env python
"""
启动脚本 - 运行公文自动排版服务
"""
import uvicorn

if __name__ == "__main__":
    print("=" * 50)
    print("公文自动排版工具")
    print("=" * 50)
    print("服务启动中...")
    print("访问地址: http://localhost:8000")
    print("API文档: http://localhost:8000/docs")
    print("前端页面: http://localhost:8000/static/index.html")
    print("=" * 50)

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
