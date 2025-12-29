# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件 - 手动复制依赖包

使用方法（在 Windows 命令行中执行）：
1. 安装依赖: pip install -r requirements.txt
2. 安装 PyInstaller: pip install pyinstaller
3. 执行打包: pyinstaller gw-formatter.spec
4. 生成的程序位于 dist/公文自动排版工具/ 目录
"""

import sys
import os
from pathlib import Path

block_cipher = None

# 项目根目录
PROJECT_DIR = Path(SPECPATH)

# 直接通过 fastapi 模块获取 site-packages 路径
import fastapi
SITE_PACKAGES = Path(fastapi.__file__).parent.parent

print(f"Site-packages 路径: {SITE_PACKAGES}")

# 需要手动复制的包列表
packages_to_copy = [
    # Web 框架
    'fastapi',
    'starlette',
    'pydantic',
    'pydantic_core',

    # 异步支持
    'anyio',
    'sniffio',

    # 服务器
    'waitress',
    'asgiref',
    'h11',

    # HTTP 客户端
    'httpcore',
    'httpx',

    # 工具库
    'dotenv',
    'click',
    'colorama',
    'idna',
    'certifi',
    'charset_normalizer',
    'annotated_types',

    # 文件处理
    'python_multipart',
    'aiofiles',

    # 文档处理
    'docx',
    'lxml',

    # AI API
    'dashscope',
    'openai',

    # 网络
    'urllib3',
    'requests',
]

# 构建 datas 列表
datas = [
    # 应用代码
    ('app', 'app'),
    # 静态文件
    ('static', 'static'),
    # 配置管理器
    ('config_manager.py', '.'),
]

# 添加依赖包
found_count = 0
for pkg_name in packages_to_copy:
    pkg_path = SITE_PACKAGES / pkg_name
    if pkg_path.exists():
        if pkg_path.is_dir():
            datas.append((str(pkg_path), pkg_name))
            found_count += 1
            print(f"  [OK] 添加包: {pkg_name}")
        else:
            datas.append((str(pkg_path), '.'))
            found_count += 1
            print(f"  [OK] 添加文件: {pkg_name}")
    else:
        print(f"  [--] 跳过包: {pkg_name}")

# 检查单文件模块
single_file_modules = [
    'typing_extensions.py',
]
for mod_name in single_file_modules:
    mod_path = SITE_PACKAGES / mod_name
    if mod_path.exists():
        datas.append((str(mod_path), '.'))
        print(f"  [OK] 添加模块: {mod_name}")

print(f"\n共找到 {found_count} 个包")

a = Analysis(
    ['run.py'],
    pathex=[str(PROJECT_DIR)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        # 标准库
        'asyncio',
        'asyncio.base_events',
        'asyncio.events',
        'asyncio.selector_events',
        'asyncio.windows_events',
        'asyncio.proactor_events',
        'concurrent.futures',
        'email.mime',
        'email.mime.text',
        'email.mime.multipart',
        'json',
        'logging',
        'logging.config',
        'logging.handlers',
        'ssl',
        'http',
        'http.cookies',
        'encodings',
        'encodings.idna',
        'encodings.utf_8',
        'encodings.ascii',
        'xml.etree.ElementTree',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',
        'scipy',
        'PIL',
        'cv2',
        'IPython',
        'jupyter',
        'notebook',
        'uvicorn',
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
    [],
    exclude_binaries=True,
    name='公文自动排版工具',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,  # 隐藏控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',  # 应用图标
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='公文自动排版工具',
)
