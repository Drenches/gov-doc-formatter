#!/usr/bin/env python
"""
启动脚本 - 运行公文自动排版服务

使用 waitress 作为 WSGI 服务器，对 PyInstaller 打包更友好
"""
import os
import sys

# 关键：在最开始设置路径
if getattr(sys, 'frozen', False):
    # PyInstaller 打包后
    BASE_DIR = sys._MEIPASS
    os.chdir(os.path.dirname(sys.executable))
else:
    # 开发模式
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

import time
import threading
import webbrowser


def is_frozen():
    """检查是否为打包后的 EXE"""
    return getattr(sys, 'frozen', False)


def open_browser():
    """延迟打开浏览器"""
    time.sleep(2)
    webbrowser.open('http://localhost:8000/static/index.html')


def run_with_waitress():
    """使用 waitress 运行服务（WSGI 方式，兼容性更好）"""
    from waitress import serve
    from asgiref.wsgi import WsgiToAsgi
    from app.main import app

    # 创建 WSGI 到 ASGI 的适配器
    # 注意：这里我们需要反过来，把 ASGI app 包装成 WSGI
    # 但 waitress 只支持 WSGI，所以我们用一个同步包装器

    # 使用 a]sync_asgi 的 ASGIMiddleware 来包装
    from asgiref.sync import async_to_sync
    import asyncio

    class WsgiApp:
        """将 ASGI 应用包装为 WSGI"""
        def __init__(self, asgi_app):
            self.asgi_app = asgi_app

        def __call__(self, environ, start_response):
            # 简单的同步包装，适用于简单场景
            # 对于生产环境，建议使用 uvicorn
            import io

            # 构建 ASGI scope
            scope = {
                'type': 'http',
                'asgi': {'version': '3.0'},
                'http_version': '1.1',
                'method': environ.get('REQUEST_METHOD', 'GET'),
                'scheme': environ.get('wsgi.url_scheme', 'http'),
                'path': environ.get('PATH_INFO', '/'),
                'query_string': environ.get('QUERY_STRING', '').encode('utf-8'),
                'root_path': environ.get('SCRIPT_NAME', ''),
                'headers': self._get_headers(environ),
                'server': (environ.get('SERVER_NAME', 'localhost'),
                          int(environ.get('SERVER_PORT', 8000))),
            }

            # 读取请求体
            try:
                content_length = int(environ.get('CONTENT_LENGTH', 0))
            except (ValueError, TypeError):
                content_length = 0

            body = environ['wsgi.input'].read(content_length) if content_length > 0 else b''

            # 运行 ASGI 应用
            response_started = False
            response_headers = []
            response_body = []
            status_code = 200

            async def receive():
                return {'type': 'http.request', 'body': body, 'more_body': False}

            async def send(message):
                nonlocal response_started, response_headers, status_code
                if message['type'] == 'http.response.start':
                    response_started = True
                    status_code = message['status']
                    response_headers.extend(message.get('headers', []))
                elif message['type'] == 'http.response.body':
                    response_body.append(message.get('body', b''))

            # 运行异步应用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.asgi_app(scope, receive, send))
            finally:
                loop.close()

            # 构建 WSGI 响应
            status = f"{status_code} OK"
            headers = [(k.decode() if isinstance(k, bytes) else k,
                       v.decode() if isinstance(v, bytes) else v)
                      for k, v in response_headers]

            start_response(status, headers)
            return response_body

        def _get_headers(self, environ):
            """从 WSGI environ 提取 HTTP 头"""
            headers = []
            for key, value in environ.items():
                if key.startswith('HTTP_'):
                    header_name = key[5:].lower().replace('_', '-')
                    headers.append((header_name.encode(), value.encode()))
                elif key == 'CONTENT_TYPE':
                    headers.append((b'content-type', value.encode()))
                elif key == 'CONTENT_LENGTH':
                    headers.append((b'content-length', value.encode()))
            return headers

    wsgi_app = WsgiApp(app)
    print("使用 waitress 服务器启动...")
    serve(wsgi_app, host='127.0.0.1', port=8000, _quiet=True)


def run_with_uvicorn():
    """使用 uvicorn 运行服务（开发模式）"""
    import uvicorn
    from app.main import app
    uvicorn.run(app, host='127.0.0.1', port=8000, log_level='warning')


def main():
    """主函数"""
    print("=" * 50)
    print("公文自动排版工具")
    print("=" * 50)
    print("服务启动中...")
    print("访问地址: http://localhost:8000")

    if not is_frozen():
        print("API文档: http://localhost:8000/docs")
        print("前端页面: http://localhost:8000/static/index.html")

    print("=" * 50)
    print("提示: 关闭此窗口将停止服务")
    print("=" * 50)

    # 打包模式下自动打开浏览器
    if is_frozen():
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

    # 根据运行环境选择服务器
    if is_frozen():
        # 打包模式使用 waitress（兼容性更好）
        run_with_waitress()
    else:
        # 开发模式使用 uvicorn（功能更全）
        run_with_uvicorn()


if __name__ == "__main__":
    main()
