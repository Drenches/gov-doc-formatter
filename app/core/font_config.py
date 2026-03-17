"""
字体配置模块 - 管理不同元素类型的字体设置
"""
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class FontConfig:
    """字体配置"""
    # 中文字体
    chinese_font: str = "仿宋_GB2312"
    # 英文数字字体
    english_font: str = "Times New Roman"
    # 是否加粗
    bold: bool = False
    # 字号（磅值）
    size: int = 16  # 默认三号字（16磅）


@dataclass
class DocumentFontConfig:
    """文档级字体配置 - 为每种元素类型配置字体"""

    # 标题字体配置
    title: FontConfig = None
    # 一级标题字体配置
    heading1: FontConfig = None
    # 二级标题字体配置
    heading2: FontConfig = None
    # 三级标题字体配置
    heading3: FontConfig = None
    # 四级标题字体配置
    heading4: FontConfig = None
    # 正文字体配置
    body: FontConfig = None
    # 发文机关字体配置
    issuing_authority: FontConfig = None
    # 成文日期字体配置
    date: FontConfig = None

    def __post_init__(self):
        """初始化默认值"""
        # 如果没有配置,使用 GB/T 9704-2012 标准
        if self.title is None:
            self.title = FontConfig(
                chinese_font="方正小标宋简体",
                english_font="Times New Roman",
                bold=False,
                size=22  # 二号字
            )

        if self.heading1 is None:
            self.heading1 = FontConfig(
                chinese_font="黑体",
                english_font="Times New Roman",
                bold=False,
                size=16  # 三号字
            )

        if self.heading2 is None:
            self.heading2 = FontConfig(
                chinese_font="楷体_GB2312",
                english_font="Times New Roman",
                bold=False,
                size=16  # 三号字
            )

        if self.heading3 is None:
            self.heading3 = FontConfig(
                chinese_font="仿宋_GB2312",
                english_font="Times New Roman",
                bold=True,  # 三级标题加粗
                size=16  # 三号字
            )

        if self.heading4 is None:
            self.heading4 = FontConfig(
                chinese_font="仿宋_GB2312",
                english_font="Times New Roman",
                bold=False,
                size=16  # 三号字
            )

        if self.body is None:
            self.body = FontConfig(
                chinese_font="仿宋_GB2312",
                english_font="Times New Roman",
                bold=False,
                size=16  # 三号字
            )

        if self.issuing_authority is None:
            self.issuing_authority = FontConfig(
                chinese_font="仿宋_GB2312",
                english_font="Times New Roman",
                bold=False,
                size=16  # 三号字
            )

        if self.date is None:
            self.date = FontConfig(
                chinese_font="仿宋_GB2312",
                english_font="Times New Roman",
                bold=False,
                size=16  # 三号字
            )

    def get_font_config(self, element_type: str) -> FontConfig:
        """
        根据元素类型获取字体配置

        Args:
            element_type: 元素类型 (title/heading1/heading2/heading3/heading4/body/issuing_authority/date)

        Returns:
            FontConfig: 字体配置
        """
        type_map = {
            "title": self.title,
            "heading1": self.heading1,
            "heading2": self.heading2,
            "heading3": self.heading3,
            "heading4": self.heading4,
            "body": self.body,
            "issuing_authority": self.issuing_authority,
            "date": self.date,
        }
        return type_map.get(element_type, self.body)

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Dict[str, str]]) -> 'DocumentFontConfig':
        """
        从字典创建配置

        Args:
            config_dict: 配置字典,格式如:
                {
                    "global_english_font": "Times New Roman",  # 或 "follow"
                    "title": {"chinese_font": "方正小标宋简体", "bold": true, "size": 22},
                    "body": {"chinese_font": "仿宋_GB2312", "bold": false, "size": 16},
                    ...
                }

        Returns:
            DocumentFontConfig: 文档字体配置
        """
        # 获取全局英文字体设置
        global_english_font = config_dict.get("global_english_font", "Times New Roman")

        kwargs = {}
        for element_type in ["title", "heading1", "heading2", "heading3", "heading4",
                            "body", "issuing_authority", "date"]:
            if element_type in config_dict:
                element_config = config_dict[element_type]
                chinese_font = element_config.get("chinese_font", "仿宋_GB2312")

                # 如果全局英文字体设置为"跟随"，则使用中文字体
                if global_english_font == "follow":
                    english_font = chinese_font
                else:
                    english_font = global_english_font

                kwargs[element_type] = FontConfig(
                    chinese_font=chinese_font,
                    english_font=english_font,
                    bold=element_config.get("bold", False),
                    size=element_config.get("size", 16)
                )

        return cls(**kwargs)

    def to_dict(self) -> Dict[str, Dict[str, str]]:
        """
        转换为字典

        Returns:
            Dict: 配置字典
        """
        return {
            "title": {
                "chinese_font": self.title.chinese_font,
                "english_font": self.title.english_font,
                "bold": self.title.bold,
                "size": self.title.size
            },
            "heading1": {
                "chinese_font": self.heading1.chinese_font,
                "english_font": self.heading1.english_font,
                "bold": self.heading1.bold,
                "size": self.heading1.size
            },
            "heading2": {
                "chinese_font": self.heading2.chinese_font,
                "english_font": self.heading2.english_font,
                "bold": self.heading2.bold,
                "size": self.heading2.size
            },
            "heading3": {
                "chinese_font": self.heading3.chinese_font,
                "english_font": self.heading3.english_font,
                "bold": self.heading3.bold,
                "size": self.heading3.size
            },
            "heading4": {
                "chinese_font": self.heading4.chinese_font,
                "english_font": self.heading4.english_font,
                "bold": self.heading4.bold,
                "size": self.heading4.size
            },
            "body": {
                "chinese_font": self.body.chinese_font,
                "english_font": self.body.english_font,
                "bold": self.body.bold,
                "size": self.body.size
            },
            "issuing_authority": {
                "chinese_font": self.issuing_authority.chinese_font,
                "english_font": self.issuing_authority.english_font,
                "bold": self.issuing_authority.bold,
                "size": self.issuing_authority.size
            },
            "date": {
                "chinese_font": self.date.chinese_font,
                "english_font": self.date.english_font,
                "bold": self.date.bold,
                "size": self.date.size
            },
        }
