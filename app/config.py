"""
配置模块 - 管理应用配置和环境变量
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent

# 文件目录配置
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"

# 确保目录存在
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# 通义千问 API 配置
DASHSCOPE_API_KEY = os.getenv("DASHSCOPE_API_KEY", "")

# 模型配置
LLM_MODEL = os.getenv("LLM_MODEL", "qwen-turbo")  # 可选: qwen-turbo, qwen-plus, qwen-max

# 文件大小限制 (10MB)
MAX_FILE_SIZE = 10 * 1024 * 1024

# 允许的文件类型
ALLOWED_EXTENSIONS = {".docx", ".doc"}
