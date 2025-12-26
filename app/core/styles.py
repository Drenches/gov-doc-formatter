"""
公文样式定义模块 - 根据《党政机关公文格式》(GB/T 9704-2012) 定义样式
"""
from docx.shared import Pt, Cm, Twips, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.enum.style import WD_STYLE_TYPE
from dataclasses import dataclass
from typing import Optional, Union


@dataclass
class FontStyle:
    """字体样式定义"""
    name: str           # 中文字体名称
    name_ascii: str     # 英文/数字字体名称
    size: Pt            # 字号（磅值）
    bold: bool = False  # 是否加粗


@dataclass
class ParagraphStyle:
    """段落样式定义"""
    alignment: WD_ALIGN_PARAGRAPH   # 对齐方式
    first_line_indent: Optional[Union[Cm, Pt]] = None  # 首行缩进
    line_spacing: Optional[Pt] = None       # 行距（磅值）
    space_before: Optional[Pt] = None       # 段前间距
    space_after: Optional[Pt] = None        # 段后间距


# ============ 字号对照表（号 -> 磅值）============
# 参考：https://zh.wikipedia.org/wiki/字号
FONT_SIZE_MAP = {
    "初号": Pt(42),
    "小初": Pt(36),
    "一号": Pt(26),
    "小一": Pt(24),
    "二号": Pt(22),
    "小二": Pt(18),
    "三号": Pt(16),
    "小三": Pt(15),
    "四号": Pt(14),
    "小四": Pt(12),
    "五号": Pt(10.5),
    "小五": Pt(9),
    "六号": Pt(7.5),
    "小六": Pt(6.5),
    "七号": Pt(5.5),
    "八号": Pt(5),
}

# ============ 首行缩进计算 ============
# 三号字（16磅）两个字符的缩进量
# 两个字符 = 16磅 × 2 = 32磅
TWO_CHAR_INDENT = Pt(32)  # 两个三号字的宽度

# ============ 行距设置 ============
LINE_SPACING_PT = Pt(28)  # 固定行距28磅


# ============ 公文字体定义 ============
class GovDocFonts:
    """党政机关公文字体定义"""

    # 方正小标宋简体 - 用于公文标题
    TITLE = FontStyle(
        name="方正小标宋简体",
        name_ascii="Times New Roman",
        size=FONT_SIZE_MAP["二号"],
        bold=False
    )

    # 黑体 - 用于一级标题
    HEADING1 = FontStyle(
        name="黑体",
        name_ascii="Times New Roman",
        size=FONT_SIZE_MAP["三号"],
        bold=False
    )

    # 楷体_GB2312 - 用于二级标题
    HEADING2 = FontStyle(
        name="楷体_GB2312",
        name_ascii="Times New Roman",
        size=FONT_SIZE_MAP["三号"],
        bold=False
    )

    # 仿宋_GB2312 - 用于三级标题、四级标题、正文
    HEADING3 = FontStyle(
        name="仿宋_GB2312",
        name_ascii="Times New Roman",
        size=FONT_SIZE_MAP["三号"],
        bold=True  # 三级标题加粗
    )

    HEADING4 = FontStyle(
        name="仿宋_GB2312",
        name_ascii="Times New Roman",
        size=FONT_SIZE_MAP["三号"],
        bold=False
    )

    BODY = FontStyle(
        name="仿宋_GB2312",
        name_ascii="Times New Roman",
        size=FONT_SIZE_MAP["三号"],
        bold=False
    )

    # 发文机关署名
    ISSUING_AUTHORITY = FontStyle(
        name="仿宋_GB2312",
        name_ascii="Times New Roman",
        size=FONT_SIZE_MAP["三号"],
        bold=False
    )

    # 成文日期
    DATE = FontStyle(
        name="仿宋_GB2312",
        name_ascii="Times New Roman",
        size=FONT_SIZE_MAP["三号"],
        bold=False
    )


# ============ 公文段落样式定义 ============
class GovDocParagraphs:
    """党政机关公文段落样式定义"""

    # 公文标题 - 居中，无首行缩进
    TITLE = ParagraphStyle(
        alignment=WD_ALIGN_PARAGRAPH.CENTER,
        first_line_indent=None,
        line_spacing=LINE_SPACING_PT,
        space_before=Pt(0),
        space_after=Pt(0)
    )

    # 一级标题 - 首行缩进2字符
    HEADING1 = ParagraphStyle(
        alignment=WD_ALIGN_PARAGRAPH.LEFT,
        first_line_indent=TWO_CHAR_INDENT,
        line_spacing=LINE_SPACING_PT,
        space_before=Pt(0),
        space_after=Pt(0)
    )

    # 二级标题 - 首行缩进2字符
    HEADING2 = ParagraphStyle(
        alignment=WD_ALIGN_PARAGRAPH.LEFT,
        first_line_indent=TWO_CHAR_INDENT,
        line_spacing=LINE_SPACING_PT,
        space_before=Pt(0),
        space_after=Pt(0)
    )

    # 三级标题 - 首行缩进2字符
    HEADING3 = ParagraphStyle(
        alignment=WD_ALIGN_PARAGRAPH.LEFT,
        first_line_indent=TWO_CHAR_INDENT,
        line_spacing=LINE_SPACING_PT,
        space_before=Pt(0),
        space_after=Pt(0)
    )

    # 四级标题 - 首行缩进2字符
    HEADING4 = ParagraphStyle(
        alignment=WD_ALIGN_PARAGRAPH.LEFT,
        first_line_indent=TWO_CHAR_INDENT,
        line_spacing=LINE_SPACING_PT,
        space_before=Pt(0),
        space_after=Pt(0)
    )

    # 正文 - 两端对齐，首行缩进2字符，行距28磅
    BODY = ParagraphStyle(
        alignment=WD_ALIGN_PARAGRAPH.JUSTIFY,
        first_line_indent=TWO_CHAR_INDENT,
        line_spacing=LINE_SPACING_PT,
        space_before=Pt(0),
        space_after=Pt(0)
    )

    # 发文机关署名 - 右对齐，无首行缩进
    ISSUING_AUTHORITY = ParagraphStyle(
        alignment=WD_ALIGN_PARAGRAPH.RIGHT,
        first_line_indent=None,
        line_spacing=LINE_SPACING_PT,
        space_before=Pt(0),
        space_after=Pt(0)
    )

    # 成文日期 - 右对齐，无首行缩进
    DATE = ParagraphStyle(
        alignment=WD_ALIGN_PARAGRAPH.RIGHT,
        first_line_indent=None,
        line_spacing=LINE_SPACING_PT,
        space_before=Pt(0),
        space_after=Pt(0)
    )


# ============ 页面设置 ============
class PageSettings:
    """公文页面设置（A4纸）"""

    # 纸张大小
    PAGE_WIDTH = Cm(21.0)   # A4宽度
    PAGE_HEIGHT = Cm(29.7)  # A4高度

    # 页边距
    MARGIN_TOP = Cm(3.7)     # 上边距 37mm
    MARGIN_BOTTOM = Cm(3.5)  # 下边距 35mm
    MARGIN_LEFT = Cm(2.8)    # 左边距 28mm
    MARGIN_RIGHT = Cm(2.6)   # 右边距 26mm

    # 版心设置
    LINES_PER_PAGE = 22      # 每页22行
    CHARS_PER_LINE = 28      # 每行28字
    LINE_SPACING = Pt(28)    # 行距固定值28磅


# ============ 段落类型枚举 ============
class ElementType:
    """文档元素类型"""
    TITLE = "title"              # 公文标题
    HEADING1 = "heading1"        # 一级标题
    HEADING2 = "heading2"        # 二级标题
    HEADING3 = "heading3"        # 三级标题
    HEADING4 = "heading4"        # 四级标题
    BODY = "body"                # 正文
    ISSUING_AUTHORITY = "issuing_authority"  # 发文机关
    DATE = "date"                # 成文日期
    ATTACHMENT = "attachment"    # 附件
    UNKNOWN = "unknown"          # 未知类型


# ============ 样式映射 ============
FONT_STYLE_MAP = {
    ElementType.TITLE: GovDocFonts.TITLE,
    ElementType.HEADING1: GovDocFonts.HEADING1,
    ElementType.HEADING2: GovDocFonts.HEADING2,
    ElementType.HEADING3: GovDocFonts.HEADING3,
    ElementType.HEADING4: GovDocFonts.HEADING4,
    ElementType.BODY: GovDocFonts.BODY,
    ElementType.ISSUING_AUTHORITY: GovDocFonts.ISSUING_AUTHORITY,
    ElementType.DATE: GovDocFonts.DATE,
}

PARAGRAPH_STYLE_MAP = {
    ElementType.TITLE: GovDocParagraphs.TITLE,
    ElementType.HEADING1: GovDocParagraphs.HEADING1,
    ElementType.HEADING2: GovDocParagraphs.HEADING2,
    ElementType.HEADING3: GovDocParagraphs.HEADING3,
    ElementType.HEADING4: GovDocParagraphs.HEADING4,
    ElementType.BODY: GovDocParagraphs.BODY,
    ElementType.ISSUING_AUTHORITY: GovDocParagraphs.ISSUING_AUTHORITY,
    ElementType.DATE: GovDocParagraphs.DATE,
}
