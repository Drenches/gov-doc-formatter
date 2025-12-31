"""
MarkerAgent - 结构标记Agent

负责识别文档中各段落的类型（标题、正文、发文机关等）
这是对现有 llm_analyzer.py 核心功能的Agent封装
"""
import json
import logging
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from app.core.agents.base_agent import BaseAgent, AgentResult
from app.core.styles import ElementType

logger = logging.getLogger(__name__)


@dataclass
class DocumentElement:
    """文档元素"""
    index: int                  # 原始段落索引
    element_type: str           # 元素类型
    content: str                # 内容
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult(AgentResult):
    """分析结果"""
    title: Optional[str] = None                    # 公文标题
    elements: List[DocumentElement] = field(default_factory=list)  # 文档元素列表
    issuing_authority: Optional[str] = None        # 发文机关
    date: Optional[str] = None                     # 成文日期
    error_message: Optional[str] = None            # 错误信息


class MarkerAgent(BaseAgent):
    """
    结构标记Agent

    识别文档中各段落的类型：
    - title: 公文标题
    - heading1-4: 各级标题
    - body: 正文
    - issuing_authority: 发文机关
    - date: 成文日期
    """

    PROMPT_TEMPLATE = """你是一个专业的公文格式分析专家。请分析以下公文内容，识别每个段落的类型。

公文内容（每行前面的数字是段落编号）：
{document_text}

请识别每个段落属于以下哪种类型：
- title: 公文标题（通常是"关于XXX的通知/报告/请示/批复"等）
- heading1: 一级标题（格式通常是"一、XXX"）
- heading2: 二级标题（格式通常是"（一）XXX"或"（二）XXX"）
- heading3: 三级标题（格式通常是"1.XXX"或"1．XXX"）
- heading4: 四级标题（格式通常是"（1）XXX"）
- body: 正文内容
- issuing_authority: 发文机关署名
- date: 成文日期（如"2025年12月25日"）

请以JSON格式返回分析结果，格式如下：
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

注意事项：
1. 请务必按照段落编号顺序返回所有非空段落
2. 如果无法确定类型，默认为body
3. 标题通常在文档开头，且内容较短
4. 一级标题通常以"一、二、三..."开头
5. 二级标题通常以"（一）（二）..."开头
6. 三级标题通常以"1. 2. 3."或"1．2．3．"开头
7. 四级标题通常以"（1）（2）..."开头
8. 发文机关和日期通常在文档末尾

请只返回JSON内容，不要有其他说明文字。"""

    @property
    def name(self) -> str:
        return "MarkerAgent"

    def get_prompt(self, document_text: str) -> str:
        """构建分析prompt"""
        return self.PROMPT_TEMPLATE.format(document_text=document_text)

    def parse_response(self, content: str) -> AnalysisResult:
        """解析LLM响应"""
        json_data = self.extract_json(content)

        if not json_data:
            logger.error(f"[{self.name}] JSON解析失败")
            return AnalysisResult(
                success=False,
                raw_response=content,
                error_message="JSON解析失败"
            )

        try:
            elements = []
            for item in json_data.get("elements", []):
                element = DocumentElement(
                    index=item.get("index", 0),
                    element_type=self._normalize_type(item.get("type", "body")),
                    content=item.get("content", "")
                )
                elements.append(element)

            logger.info(f"[{self.name}] 解析完成，识别到{len(elements)}个元素")

            return AnalysisResult(
                success=True,
                title=json_data.get("title"),
                elements=elements,
                issuing_authority=json_data.get("issuing_authority"),
                date=json_data.get("date"),
                raw_response=content
            )

        except Exception as e:
            logger.error(f"[{self.name}] 解析异常: {str(e)}")
            return AnalysisResult(
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
        }
        return type_map.get(type_str.lower(), ElementType.BODY)

    def analyze(self, document_text: str) -> AnalysisResult:
        """
        分析文档结构

        Args:
            document_text: 带段落编号的文档文本（格式：[0] 内容\n[1] 内容...）

        Returns:
            AnalysisResult: 分析结果
        """
        result = self.execute(document_text)

        # 转换为 AnalysisResult
        if isinstance(result, AnalysisResult):
            return result

        # 如果基类返回了 AgentResult，转换一下
        return AnalysisResult(
            success=result.success,
            raw_response=result.raw_response,
            error_message=result.error
        )
