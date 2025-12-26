"""
LLM分析模块 - 使用通义千问分析公文结构
"""
import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
import dashscope
from dashscope import Generation

from app.config import DASHSCOPE_API_KEY, LLM_MODEL
from app.core.styles import ElementType


@dataclass
class DocumentElement:
    """文档元素"""
    index: int                  # 原始段落索引
    element_type: str           # 元素类型
    content: str                # 内容
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResult:
    """分析结果"""
    title: Optional[str]                    # 公文标题
    elements: List[DocumentElement]         # 文档元素列表
    issuing_authority: Optional[str]        # 发文机关
    date: Optional[str]                     # 成文日期
    raw_response: str                       # LLM原始响应
    success: bool = True                    # 是否成功
    error_message: Optional[str] = None     # 错误信息


# 公文结构分析的Prompt模板
ANALYSIS_PROMPT = """你是一个专业的公文格式分析专家。请分析以下公文内容，识别每个段落的类型。

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


class LLMAnalyzer:
    """使用通义千问分析公文结构"""

    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化分析器

        Args:
            api_key: 通义千问API密钥，如果不提供则从配置读取
            model: 模型名称，如果不提供则从配置读取
        """
        self.api_key = api_key or DASHSCOPE_API_KEY
        self.model = model or LLM_MODEL

        if not self.api_key:
            raise ValueError("未配置DASHSCOPE_API_KEY，请在.env文件中设置")

        dashscope.api_key = self.api_key

    def analyze(self, document_text: str) -> AnalysisResult:
        """
        分析文档结构

        Args:
            document_text: 带段落编号的文档文本

        Returns:
            AnalysisResult: 分析结果
        """
        prompt = ANALYSIS_PROMPT.format(document_text=document_text)

        try:
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                result_format='message'
            )

            if response.status_code != 200:
                return AnalysisResult(
                    title=None,
                    elements=[],
                    issuing_authority=None,
                    date=None,
                    raw_response=str(response),
                    success=False,
                    error_message=f"API调用失败: {response.message}"
                )

            # 提取响应内容
            content = response.output.choices[0].message.content
            return self._parse_response(content)

        except Exception as e:
            return AnalysisResult(
                title=None,
                elements=[],
                issuing_authority=None,
                date=None,
                raw_response="",
                success=False,
                error_message=f"分析失败: {str(e)}"
            )

    def _parse_response(self, content: str) -> AnalysisResult:
        """
        解析LLM响应

        Args:
            content: LLM响应内容

        Returns:
            AnalysisResult: 解析后的结果
        """
        try:
            # 尝试提取JSON部分
            json_str = self._extract_json(content)
            data = json.loads(json_str)

            elements = []
            for item in data.get("elements", []):
                element = DocumentElement(
                    index=item.get("index", 0),
                    element_type=self._normalize_type(item.get("type", "body")),
                    content=item.get("content", "")
                )
                elements.append(element)

            return AnalysisResult(
                title=data.get("title"),
                elements=elements,
                issuing_authority=data.get("issuing_authority"),
                date=data.get("date"),
                raw_response=content,
                success=True
            )

        except json.JSONDecodeError as e:
            return AnalysisResult(
                title=None,
                elements=[],
                issuing_authority=None,
                date=None,
                raw_response=content,
                success=False,
                error_message=f"JSON解析失败: {str(e)}"
            )

    def _extract_json(self, content: str) -> str:
        """
        从响应中提取JSON字符串

        Args:
            content: 响应内容

        Returns:
            str: JSON字符串
        """
        # 尝试匹配```json ... ```格式
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            return json_match.group(1)

        # 尝试匹配``` ... ```格式
        code_match = re.search(r'```\s*([\s\S]*?)\s*```', content)
        if code_match:
            return code_match.group(1)

        # 尝试直接匹配JSON对象
        json_obj_match = re.search(r'\{[\s\S]*\}', content)
        if json_obj_match:
            return json_obj_match.group(0)

        return content

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


def analyze_document(document_text: str, api_key: str = None) -> AnalysisResult:
    """
    便捷函数：分析文档

    Args:
        document_text: 文档文本
        api_key: API密钥（可选）

    Returns:
        AnalysisResult: 分析结果
    """
    analyzer = LLMAnalyzer(api_key=api_key)
    return analyzer.analyze(document_text)
