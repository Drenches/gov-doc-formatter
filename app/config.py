"""
配置模块 - 管理应用配置和环境变量
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


def get_base_dir() -> Path:
    """
    获取应用程序基础目录

    - 开发模式：项目根目录
    - 打包模式：EXE 临时解压目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        return Path(sys._MEIPASS)
    else:
        # 开发模式
        return Path(__file__).resolve().parent.parent


def get_data_dir() -> Path:
    """
    获取数据存储目录

    - 开发模式：项目根目录
    - 打包模式：用户配置的目录 或 默认用户目录
    """
    if getattr(sys, 'frozen', False):
        # 打包模式：优先使用 config_manager 中配置的目录
        try:
            from config_manager import config_manager
            return Path(config_manager.get_data_dir())
        except ImportError:
            # 回退到默认目录
            if sys.platform == 'win32':
                base = Path(os.environ.get('USERPROFILE', Path.home()))
            else:
                base = Path.home()
            return base / ".公文排版工具"
    else:
        # 开发模式：项目根目录
        return Path(__file__).resolve().parent.parent


# 项目根目录（用于访问 app 和 static）
BASE_DIR = get_base_dir()

# 数据目录（用于 uploads 和 outputs）
DATA_DIR = get_data_dir()

# 文件目录配置
UPLOAD_DIR = DATA_DIR / "uploads"
OUTPUT_DIR = DATA_DIR / "outputs"

# 确保目录存在
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_api_key() -> str:
    """
    获取 API Key

    优先级：
    1. 环境变量 DASHSCOPE_API_KEY
    2. 本地配置文件
    """
    # 首先检查环境变量
    api_key = os.getenv("DASHSCOPE_API_KEY", "")
    if api_key:
        return api_key

    # 然后检查本地配置
    try:
        # 延迟导入避免循环依赖
        from config_manager import config_manager
        return config_manager.get_api_key() or ""
    except ImportError:
        return ""


# 通义千问 API 配置
DASHSCOPE_API_KEY = get_api_key()

# 可用的模型列表
AVAILABLE_MODELS = [
    {"id": "qwen-plus", "name": "Qwen-Plus", "description": "平衡性能与成本"},
    {"id": "qwen-turbo", "name": "Qwen-Turbo", "description": "快速响应"},
    {"id": "qwen-max", "name": "Qwen-Max", "description": "最高性能"},
    {"id": "qwen-flash", "name": "Qwen-Flash", "description": "超快速响应"},
    {"id": "qwen-long-latest", "name": "Qwen-Long-Latest", "description": "长文本处理"},
    {"id": "qwen-long-2025-01-25", "name": "Qwen-Long (2025-01-25)", "description": "长文本处理 (稳定版)"}
]


def get_current_model() -> str:
    """
    获取当前使用的模型

    优先级:
    1. 环境变量 LLM_MODEL
    2. 本地配置文件
    3. 默认值 qwen-turbo
    """
    # 首先检查环境变量
    model = os.getenv("LLM_MODEL", "")
    if model:
        return model

    # 然后检查本地配置
    try:
        from config_manager import config_manager
        return config_manager.get_model()
    except ImportError:
        return "qwen-turbo"


# 模型配置
LLM_MODEL = get_current_model()

# 文件大小限制 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# 允许的文件类型
ALLOWED_EXTENSIONS = {".docx", ".doc"}


def reload_api_key():
    """重新加载 API Key（用于配置更新后）"""
    global DASHSCOPE_API_KEY
    DASHSCOPE_API_KEY = get_api_key()
    # 同时更新环境变量
    if DASHSCOPE_API_KEY:
        os.environ["DASHSCOPE_API_KEY"] = DASHSCOPE_API_KEY


def reload_model():
    """重新加载模型配置（用于模型切换后）"""
    global LLM_MODEL
    LLM_MODEL = get_current_model()
    # 同时更新环境变量
    os.environ["LLM_MODEL"] = LLM_MODEL
