"""
本地配置管理器 - 管理 API Key 和应用配置
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional


def get_app_data_dir() -> Path:
    """
    获取应用数据目录

    Windows: C:/Users/<用户名>/.公文排版工具/
    Linux/Mac: ~/.公文排版工具/
    """
    if sys.platform == 'win32':
        # Windows 使用 USERPROFILE
        base = Path(os.environ.get('USERPROFILE', Path.home()))
    else:
        base = Path.home()

    app_dir = base / ".公文排版工具"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def get_base_dir() -> Path:
    """
    获取应用程序基础目录

    - 开发模式：项目根目录
    - 打包模式：EXE 所在目录或临时解压目录
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller 打包后的路径
        return Path(sys._MEIPASS)
    else:
        # 开发模式
        return Path(__file__).resolve().parent


class ConfigManager:
    """本地配置管理器"""

    def __init__(self):
        self.app_dir = get_app_data_dir()
        self.config_file = self.app_dir / "config.json"
        self.uploads_dir = self.app_dir / "uploads"
        self.outputs_dir = self.app_dir / "outputs"

        # 确保目录存在
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def load_config(self) -> dict:
        """加载配置文件"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def save_config(self, config: dict):
        """保存配置文件"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

    def get_api_key(self) -> Optional[str]:
        """获取 API Key"""
        config = self.load_config()
        return config.get("api_key")

    def set_api_key(self, api_key: str):
        """设置 API Key"""
        config = self.load_config()
        config["api_key"] = api_key
        self.save_config(config)

    def has_api_key(self) -> bool:
        """检查是否已配置 API Key"""
        api_key = self.get_api_key()
        return bool(api_key and api_key.strip())

    def clear_api_key(self):
        """清除 API Key"""
        config = self.load_config()
        config.pop("api_key", None)
        self.save_config(config)


# 全局配置管理器实例
config_manager = ConfigManager()
