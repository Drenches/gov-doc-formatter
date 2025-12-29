# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件

使用方法（在 Windows 命令行中执行）：
1. 安装 PyInstaller: pip install pyinstaller
2. 执行打包: pyinstaller gw-formatter.spec
3. 生成的 EXE 位于 dist/ 目录

注意事项：
- 需要在 Windows 环境下执行打包
- 确保已安装所有依赖: pip install -r requirements.txt
- 打包前建议先测试 run.py 是否正常运行
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
PROJECT_DIR = Path(SPECPATH)

a = Analysis(
    ['run.py'],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=[
        # 应用代码
        ('app', 'app'),
        # 静态文件
        ('static', 'static'),
        # 配置管理器
        ('config_manager.py', '.'),
    ],
    hiddenimports=[
        # FastAPI 相关
        'fastapi',
        'fastapi.responses',
        'fastapi.staticfiles',
        'fastapi.templating',
        'starlette',
        'starlette.responses',
        'starlette.staticfiles',
        'starlette.routing',

        # Uvicorn 相关
        'uvicorn',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.logging',

        # Pydantic 相关
        'pydantic',
        'pydantic_core',

        # 阿里云 DashScope
        'dashscope',
        'dashscope.api_key',

        # python-docx
        'docx',
        'docx.oxml',
        'docx.oxml.ns',

        # 其他
        'python_multipart',
        'aiofiles',
        'dotenv',
        'anyio',
        'anyio._backends',
        'anyio._backends._asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 排除不需要的模块
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='公文自动排版工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 隐藏控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',  # 如果有图标文件，取消注释此行
)
