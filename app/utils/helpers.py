"""
辅助函数模块
"""
import re
from typing import List, Tuple


def split_by_font_type(text: str) -> List[Tuple[str, bool]]:
    """
    将文本按中文和非中文分割

    Args:
        text: 输入文本

    Returns:
        List[Tuple[str, bool]]: (文本片段, 是否为中文) 的列表
    """
    result = []
    pattern = r'([\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+|[^\u4e00-\u9fff\u3000-\u303f\uff00-\uffef]+)'
    segments = re.findall(pattern, text)

    for segment in segments:
        if segment:
            is_chinese = bool(re.match(r'[\u4e00-\u9fff]', segment))
            result.append((segment, is_chinese))

    return result


def chinese_to_arabic(chinese_num: str) -> int:
    """
    将中文数字转换为阿拉伯数字

    Args:
        chinese_num: 中文数字字符串

    Returns:
        int: 阿拉伯数字
    """
    chinese_digits = {
        '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
        '十': 10, '百': 100, '千': 1000, '万': 10000
    }

    result = 0
    temp = 0
    for char in chinese_num:
        if char in chinese_digits:
            num = chinese_digits[char]
            if num >= 10:
                if temp == 0:
                    temp = 1
                result += temp * num
                temp = 0
            else:
                temp = num

    return result + temp


def detect_heading_level(text: str) -> str:
    """
    根据文本内容检测标题级别

    Args:
        text: 段落文本

    Returns:
        str: 标题类型或 'body'
    """
    text = text.strip()

    # 一级标题: 一、二、三、...
    if re.match(r'^[一二三四五六七八九十]+、', text):
        return 'heading1'

    # 二级标题: （一）（二）...
    if re.match(r'^（[一二三四五六七八九十]+）', text):
        return 'heading2'

    # 三级标题: 1. 2. 3. 或 1．2．3．
    if re.match(r'^\d+[.．]', text):
        return 'heading3'

    # 四级标题: （1）（2）...
    if re.match(r'^（\d+）', text):
        return 'heading4'

    return 'body'


def format_date_chinese(date_str: str) -> str:
    """
    将日期格式化为公文日期格式

    Args:
        date_str: 日期字符串

    Returns:
        str: 格式化后的日期 (如 "2025年12月25日")
    """
    import re
    from datetime import datetime

    # 尝试匹配各种日期格式
    patterns = [
        r'(\d{4})[-/年](\d{1,2})[-/月](\d{1,2})[日]?',
        r'(\d{4})(\d{2})(\d{2})',
    ]

    for pattern in patterns:
        match = re.match(pattern, date_str)
        if match:
            year, month, day = match.groups()
            return f"{year}年{int(month)}月{int(day)}日"

    return date_str


def validate_document_structure(elements: list) -> dict:
    """
    验证文档结构是否符合公文规范

    Args:
        elements: 文档元素列表

    Returns:
        dict: 验证结果 {valid: bool, warnings: list, errors: list}
    """
    warnings = []
    errors = []

    # 检查是否有标题
    has_title = any(e.get('type') == 'title' for e in elements)
    if not has_title:
        warnings.append("未检测到公文标题")

    # 检查标题顺序
    heading_levels = []
    for e in elements:
        etype = e.get('type', '')
        if etype.startswith('heading'):
            level = int(etype[-1])
            heading_levels.append(level)

    # 检查标题层级是否连续
    for i in range(1, len(heading_levels)):
        if heading_levels[i] > heading_levels[i-1] + 1:
            warnings.append(f"标题层级跳跃: 从{heading_levels[i-1]}级跳到{heading_levels[i]}级")

    return {
        'valid': len(errors) == 0,
        'warnings': warnings,
        'errors': errors
    }
