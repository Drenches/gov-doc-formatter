"""
本地配置管理器 - 管理 API Key 和应用配置
"""
import json
import os
import sys
from pathlib import Path
from typing import Optional


def get_default_data_dir() -> Path:
    """
    获取默认数据目录

    Windows: C:/Users/<用户名>/.公文排版工具/
    Linux/Mac: ~/.公文排版工具/
    """
    if sys.platform == 'win32':
        base = Path(os.environ.get('USERPROFILE', Path.home()))
    else:
        base = Path.home()
    return base / ".公文排版工具"


def get_bootstrap_config_path() -> Path:
    """
    获取引导配置文件路径（存储数据目录位置）
    这个文件始终在默认位置，用于记录用户选择的数据目录
    """
    default_dir = get_default_data_dir()
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir / "bootstrap.json"


def get_base_dir() -> Path:
    """
    获取应用程序基础目录

    - 开发模式：项目根目录
    - 打包模式：EXE 所在目录或临时解压目录
    """
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS)
    else:
        return Path(__file__).resolve().parent


class ConfigManager:
    """本地配置管理器"""

    def __init__(self):
        # 先读取引导配置，确定数据目录位置
        self.bootstrap_path = get_bootstrap_config_path()
        self.app_dir = self._get_data_dir()
        self.config_file = self.app_dir / "config.json"
        self.uploads_dir = self.app_dir / "uploads"
        self.outputs_dir = self.app_dir / "outputs"

        # 确保目录存在
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.outputs_dir.mkdir(parents=True, exist_ok=True)

    def _get_data_dir(self) -> Path:
        """获取数据目录，优先使用用户配置的路径"""
        bootstrap = self._load_bootstrap()
        custom_path = bootstrap.get("data_dir")
        if custom_path and Path(custom_path).exists():
            return Path(custom_path)
        return get_default_data_dir()

    def _load_bootstrap(self) -> dict:
        """加载引导配置"""
        if self.bootstrap_path.exists():
            try:
                with open(self.bootstrap_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_bootstrap(self, config: dict):
        """保存引导配置"""
        with open(self.bootstrap_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

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

    def get_data_dir(self) -> str:
        """获取当前数据目录路径"""
        return str(self.app_dir)

    def set_data_dir(self, path: str):
        """
        设置数据目录路径

        Args:
            path: 新的数据目录路径
        """
        new_path = Path(path)

        # 创建新目录
        new_path.mkdir(parents=True, exist_ok=True)
        (new_path / "uploads").mkdir(parents=True, exist_ok=True)
        (new_path / "outputs").mkdir(parents=True, exist_ok=True)

        # 如果原目录有配置文件，复制到新目录
        if self.config_file.exists():
            old_config = self.load_config()
            new_config_file = new_path / "config.json"
            with open(new_config_file, 'w', encoding='utf-8') as f:
                json.dump(old_config, f, ensure_ascii=False, indent=2)

        # 保存到引导配置
        bootstrap = self._load_bootstrap()
        bootstrap["data_dir"] = str(new_path)
        self._save_bootstrap(bootstrap)

        # 更新当前实例的路径
        self.app_dir = new_path
        self.config_file = new_path / "config.json"
        self.uploads_dir = new_path / "uploads"
        self.outputs_dir = new_path / "outputs"

    def is_first_run(self) -> bool:
        """检查是否为首次运行（未配置 API Key 或数据目录）"""
        bootstrap = self._load_bootstrap()
        # 如果没有设置过数据目录，认为是首次运行
        if "data_dir" not in bootstrap:
            return True
        return not self.has_api_key()

    def get_default_data_dir_str(self) -> str:
        """获取默认数据目录路径字符串"""
        return str(get_default_data_dir())


# 全局配置管理器实例
config_manager = ConfigManager()
