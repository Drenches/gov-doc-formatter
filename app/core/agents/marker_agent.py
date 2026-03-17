"""
MarkerAgent - 排版规划器（Layout Planner）

核心升级：
- 不再是"按规则打标签"
- 而是"综合判断文章该怎么排版"
- 输出"排版决策"，不是"推理结果"

核心红线：
- ❌ 不改变文字内容
- ✅ 只决定"这段话用什么样式"
"""
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.core.agents.base_agent import BaseAgent, AgentResult
from app.core.styles import ElementType

logger = logging.getLogger(__name__)


@dataclass
class DocumentElement:
    """文档元素"""
    index: int                  # 原始段落索引
    element_type: str           # 元素类型（排版样式）
    content: str                # 内容
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LayoutResult(AgentResult):
    """排版规划结果"""
    title: Optional[str] = None                    # 公文标题
    elements: List[DocumentElement] = field(default_factory=list)  # 文档元素列表
    issuing_authority: Optional[str] = None        # 发文机关
    date: Optional[str] = None                     # 成文日期
    error_message: Optional[str] = None            # 错误信息


# 保持向后兼容的别名
AnalysisResult = LayoutResult


class MarkerAgent(BaseAgent):
    """
    排版规划器（Layout Planner）

    核心理念：
    - 本任务目标是"安全排版"，不是"优化结构"
    - 如果存在多种可能的排版方式，选择最保守、最少层级的方案
    - 让 LLM 判断"合法结构"，而不是死规则

    4 条负约束（比正规则更重要）：
    1. 不得假设必须存在一级标题
    2. 允许以下合法结构：无任何层级标题 / 只有数字条款 / 直接正文分段
    3. 不得为了"结构美观"创造标题
    4. 如果不确定，宁可全部标记为 body
    """

    PROMPT_TEMPLATE = """你是公文排版规划专家。请为以下文档规划排版样式。

【核心任务】
为每个段落指定一个排版样式，用于在 Word 中应用格式。

公文内容（每行前面的数字是段落索引）：
{document_text}

{style_description}

【重要原则 - 安全排版】
本任务目标是"安全排版"，不是"优化结构"。

1. 如果公文中已经存在下述【判断规则】中的层级标题，则按规则标记。

2. 如果公文中不存在任何层级标题，则由你根据语义判断应该如何标记。

3. 不得假设必须存在层级标题
   - 很多公文（声明、公告、通告）本来就没有"一、二、三"
   - 没有层级标题是完全合法的

【判断规则】
- 以"一、""二、""三、"等开头 → heading1
- 以"（一）""（二）"等开头 → heading2
- 以"1.""2.""3."等开头 → heading3
- 以"（1）""（2）"等开头 → heading4
- 以"第X条""第X章"开头 → heading1
- 文档标题（通常是"关于...的通知/声明/规定"等） → title
- 右下角的机关名称 → issuing_authority
- 右下角的日期 → date
- 其他所有内容 → body

【严格禁止】
❌ **绝对不要修改段落内容**
❌ **绝对不要将中文句号(。)改成英文句点(.)**
❌ **绝对不要修改任何标点符号**
❌ **绝对不要润色或重写文字**
- 只标记样式,不改内容

请以 JSON 格式返回：
```json
{{
    "title": "公文标题内容",
    "issuing_authority": "发文机关名称（如果有）",
    "date": "成文日期（如果有）",
    "elements": [
        {{"index": 0, "type": "title", "content": "段落内容"}},
        {{"index": 1, "type": "body", "content": "段落内容"}},
        ...
    ]
}}
```

注意：elements 必须包含所有段落，index 从 0 开始。"""

    @property
    def name(self) -> str:
        return "MarkerAgent"

    def _generate_style_description(self, font_config=None) -> str:
        """
        根据字体配置生成排版样式说明

        Args:
            font_config: DocumentFontConfig 对象，如果为 None 则使用 GB/T 9704-2012 默认配置

        Returns:
            str: 排版样式说明文本
        """
        # 判断英文数字字体设置
        if font_config is None:
            # 默认 GB/T 9704-2012 配置
            english_font_desc = "Times New Roman"
        else:
            # 检查是否所有元素的英文字体都相同
            fonts = set()
            for element_type in ["title", "heading1", "heading2", "heading3", "heading4",
                                "body", "issuing_authority", "date"]:
                cfg = font_config.get_font_config(element_type)
                fonts.add(cfg.english_font)

            if len(fonts) == 1:
                english_font = fonts.pop()
                # 判断是否跟随中文字体
                title_cfg = font_config.get_font_config("title")
                if english_font == title_cfg.chinese_font:
                    english_font_desc = "跟随中文字体"
                else:
                    english_font_desc = english_font
            else:
                english_font_desc = "Times New Roman"  # 理论上不会出现这种情况

        # 获取各元素的字体配置
        if font_config is None:
            # GB/T 9704-2012 默认配置
            return f"""【可用的排版样式】
- title: 公文标题（居中、二号方正小标宋）
- heading1: 一级标题（三号黑体，用于"一、二、三..."开头的段落）
- heading2: 二级标题（三号楷体，用于"（一）（二）..."开头的段落）
- heading3: 三级标题（三号仿宋加粗，用于"1. 2. 3."开头的段落）
- heading4: 四级标题（三号仿宋，用于"（1）（2）..."开头的段落）
- body: 正文（三号仿宋，首行缩进两字符）
- issuing_authority: 发文机关署名（三号仿宋，右对齐）
- date: 成文日期（三号仿宋，右对齐）
- 英文数字字体：{english_font_desc}"""
        else:
            # 自定义配置
            title_cfg = font_config.get_font_config("title")
            h1_cfg = font_config.get_font_config("heading1")
            h2_cfg = font_config.get_font_config("heading2")
            h3_cfg = font_config.get_font_config("heading3")
            h4_cfg = font_config.get_font_config("heading4")
            body_cfg = font_config.get_font_config("body")
            auth_cfg = font_config.get_font_config("issuing_authority")
            date_cfg = font_config.get_font_config("date")

            # 字号映射
            size_map = {22: "二号", 24: "小二号", 16: "三号", 18: "小三号", 14: "四号"}

            def format_style(cfg):
                size_name = size_map.get(cfg.size, f"{cfg.size}磅")
                bold_text = "加粗" if cfg.bold else ""
                return f"{size_name}{cfg.chinese_font}{bold_text}"

            return f"""【可用的排版样式】
- title: 公文标题（居中、{format_style(title_cfg)}）
- heading1: 一级标题（{format_style(h1_cfg)}，用于"一、二、三..."开头的段落）
- heading2: 二级标题（{format_style(h2_cfg)}，用于"（一）（二）..."开头的段落）
- heading3: 三级标题（{format_style(h3_cfg)}，用于"1. 2. 3."开头的段落）
- heading4: 四级标题（{format_style(h4_cfg)}，用于"（1）（2）..."开头的段落）
- body: 正文（{format_style(body_cfg)}，首行缩进两字符）
- issuing_authority: 发文机关署名（{format_style(auth_cfg)}，右对齐）
- date: 成文日期（{format_style(date_cfg)}，右对齐）
- 英文数字字体：{english_font_desc}"""

    def get_prompt(self, document_text: str, font_config=None) -> str:
        """
        构建分析prompt

        Args:
            document_text: 文档文本
            font_config: DocumentFontConfig 对象（可选）
        """
        style_description = self._generate_style_description(font_config)
        return self.PROMPT_TEMPLATE.format(
            document_text=document_text,
            style_description=style_description
        )

    def parse_response(self, content: str) -> LayoutResult:
        """解析LLM响应"""
        json_data = self.extract_json(content)

        if not json_data:
            logger.error(f"[{self.name}] JSON解析失败")
            return LayoutResult(
                success=False,
                raw_response=content,
                error_message="JSON解析失败"
            )

        try:
            elements = []
            for item in json_data.get("elements", []):
                # 纠正内容中的英文句点为中文句号
                content_text = item.get("content", "")
                content_text = self._fix_punctuation(content_text)

                element = DocumentElement(
                    index=item.get("index", 0),
                    element_type=self._normalize_type(item.get("type", "body")),
                    content=content_text
                )
                elements.append(element)

            logger.info(f"[{self.name}] 解析完成，识别到{len(elements)}个元素")

            # 纠正title和其他字段中的标点
            title = json_data.get("title")
            if title:
                title = self._fix_punctuation(title)

            issuing_authority = json_data.get("issuing_authority")
            if issuing_authority:
                issuing_authority = self._fix_punctuation(issuing_authority)

            date = json_data.get("date")
            if date:
                date = self._fix_punctuation(date)

            return LayoutResult(
                success=True,
                title=title,
                elements=elements,
                issuing_authority=issuing_authority,
                date=date,
                raw_response=content
            )

        except Exception as e:
            logger.error(f"[{self.name}] 解析异常: {str(e)}")
            return LayoutResult(
                success=False,
                raw_response=content,
                error_message=f"解析失败: {str(e)}"
            )

    def _normalize_type(self, type_str: str) -> str:
        """
        标准化元素类型

        Args:
            type_str: 类型字符串

        Returns:
            str: 标准化后的类型
        """
        type_map = {
            "title": ElementType.TITLE,
            "heading1": ElementType.HEADING1,
            "heading2": ElementType.HEADING2,
            "heading3": ElementType.HEADING3,
            "heading4": ElementType.HEADING4,
            "body": ElementType.BODY,
            "issuing_authority": ElementType.ISSUING_AUTHORITY,
            "date": ElementType.DATE,
            # 条款式文档的类型映射
            "article": ElementType.HEADING1,
            "chapter": ElementType.HEADING1,
            "section": ElementType.HEADING2,
        }
        return type_map.get(type_str.lower(), ElementType.BODY)

    def _fix_punctuation(self, text: str) -> str:
        """
        纠正文本中的标点符号错误

        主要修复: 英文句点(.)被错误地替换中文句号(。)的问题

        Args:
            text: 待修复的文本

        Returns:
            str: 修复后的文本
        """
        if not text:
            return text

        import re

        # 规则1: 句尾的英文句点替换为中文句号
        # 匹配: 中文字符后紧跟英文句点, 并且后面是空格/换行/结尾
        text = re.sub(r'([\u4e00-\u9fa5])\s*\.\s*($|\n|\r)', r'\1。\2', text)

        # 规则2: 处理可能出现的"。."或".。"混用情况
        text = text.replace('。.', '。')
        text = text.replace('.。', '。')

        return text

    def analyze(self, document_text: str, font_config=None) -> LayoutResult:
        """
        分析文档结构，规划排版

        Args:
            document_text: 带段落编号的文档文本（格式：[0] 内容\n[1] 内容...）
            font_config: DocumentFontConfig 对象（可选），用于生成排版规则说明

        Returns:
            LayoutResult: 排版规划结果
        """
        logger.info(f"[{self.name}] 开始排版规划")

        result = self.execute(document_text, font_config)

        if isinstance(result, LayoutResult):
            return result

        # 如果基类返回了 AgentResult，转换一下
        return LayoutResult(
            success=result.success,
            raw_response=result.raw_response,
            error_message=result.error
        )

    def fallback_layout(self, lines: List[str]) -> LayoutResult:
        """
        保守兜底排版

        当 LLM 失败或结果不可信时使用
        策略：title + 全 body

        Args:
            lines: 文本行列表

        Returns:
            LayoutResult: 保守的排版结果
        """
        logger.warning(f"[{self.name}] 使用保守兜底排版")

        elements = []
        title = None

        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue

            if i == 0 and len(line) < 100:
                # 第一行且不太长，可能是标题
                element_type = ElementType.TITLE
                title = line
            else:
                element_type = ElementType.BODY

            elements.append(DocumentElement(
                index=i,
                element_type=element_type,
                content=line
            ))

        return LayoutResult(
            success=True,
            title=title,
            elements=elements
        )
