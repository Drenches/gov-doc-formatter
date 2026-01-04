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
    """使用 waitress 运行服务（备用方案）"""
    from waitress import serve
    from app.main import app
    import asyncio

    class WsgiApp:
        """将 ASGI 应用包装为 WSGI，支持流式响应（如文件下载）"""
        def __init__(self, asgi_app):
            self.asgi_app = asgi_app

        def __call__(self, environ, start_response):
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

            # 用于收集响应
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
                    body_content = message.get('body', b'')
                    if body_content:
                        response_body.append(body_content)

            # 运行异步应用
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.asgi_app(scope, receive, send))
            finally:
                loop.close()

            # 构建 WSGI 响应状态
            status_phrases = {
                200: 'OK', 201: 'Created', 204: 'No Content',
                301: 'Moved Permanently', 302: 'Found', 304: 'Not Modified',
                400: 'Bad Request', 401: 'Unauthorized', 403: 'Forbidden',
                404: 'Not Found', 405: 'Method Not Allowed',
                500: 'Internal Server Error', 502: 'Bad Gateway', 503: 'Service Unavailable'
            }
            status_phrase = status_phrases.get(status_code, 'Unknown')
            status = f"{status_code} {status_phrase}"

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
    print("  使用 waitress 服务器启动...")
    print()
    serve(wsgi_app, host='0.0.0.0', port=8000, _quiet=True)


def run_with_uvicorn(port=8080):
    """使用 uvicorn 运行服务"""
    import uvicorn
    from app.main import app
    uvicorn.run(app, host='0.0.0.0', port=port, log_level='warning')


def get_local_ip():
    """获取本机 IP 地址（用于 WSL 等环境）"""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"


def main():
    """主函数"""
    port = 8000 if is_frozen() else 8080
    local_ip = get_local_ip()

    print("=" * 50)
    print("       公文自动排版工具")
    print("=" * 50)
    print()
    print("  服务启动中...")
    print()
    print(f"  本地访问: http://localhost:{port}/static/index.html")
    print(f"  网络访问: http://{local_ip}:{port}/static/index.html")

    if not is_frozen():
        print()
        print(f"  API文档:  http://localhost:{port}/docs")

    print()
    print("=" * 50)
    print("  【重要提示】")
    print("  - 关闭此窗口将停止服务")
    print("  - WSL 环境请使用「网络访问」地址")
    print("  - 按 Ctrl+C 可停止服务")
    print("=" * 50)
    print()

    # 打包模式下自动打开浏览器
    if is_frozen():
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()

    # 统一使用 uvicorn
    run_with_uvicorn(port=port)


if __name__ == "__main__":
    main()
