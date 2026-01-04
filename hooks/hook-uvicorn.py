"""
PyInstaller hook for uvicorn
"""
from PyInstaller.utils.hooks import collect_all, collect_submodules

# 收集 uvicorn 的所有内容
datas, binaries, hiddenimports = collect_all('uvicorn')

# 额外添加子模块
hiddenimports += collect_submodules('uvicorn')
hiddenimports += [
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.loops.asyncio',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'uvicorn.lifespan.off',
    'uvicorn.main',
    'uvicorn.config',
    'uvicorn.server',
]
