#!/usr/bin/env python
"""
启动脚本 - 运行公文自动排版服务
"""
import os
import sys
import time
import threading
import webbrowser

# 添加项目根目录到路径
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后
    BASE_DIR = sys._MEIPASS
else:
    # 开发模式
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)


def is_frozen():
    """检查是否为打包后的 EXE"""
    return getattr(sys, 'frozen', False)


def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)  # 等待服务启动
    webbrowser.open('http://localhost:8000/static/index.html')


def main():
    """主函数"""
    import uvicorn

    print("=" * 50)
    print("公文自动排版工具")
    print("=" * 50)
    print("服务启动中...")
    print("访问地址: http://localhost:8000")

    if not is_frozen():
        print("API文档: http://localhost:8000/docs")
        print("前端页面: http://localhost:8000/static/index.html")

    print("=" * 50)

    # 打包模式下自动打开浏览器
    if is_frozen():
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

    # 启动服务
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=not is_frozen(),  # 打包后禁用热重载
        log_level="warning" if is_frozen() else "info"
    )


if __name__ == "__main__":
    main()
