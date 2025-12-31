"""
CleanerAgent - 文本清洗Agent

负责将不符合公文规范的文本转换为规范格式
"""
import logging
from dataclasses import dataclass
from typing import List, Optional

from app.core.agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


@dataclass
class CleanerResult(AgentResult):
    """清洗结果"""
    cleaned_text: str = ""
    changes_made: List[str] = None

    def __post_init__(self):
        if self.changes_made is None:
            self.changes_made = []


class CleanerAgent(BaseAgent):
    """
    文本清洗Agent

    将不符合公文规范的文本转换为规范格式：
    - 删除Markdown标记
    - 删除emoji和特殊符号
    - 规范标题层级编号
    - 合理划分段落
    """

    PROMPT_TEMPLATE = """你是公文格式规范化专家。请将以下文本转换为符合党政机关公文行文规范的格式。

需要处理的问题：
{issues}

原始文本：
{text}

规范化要求：
1. 删除所有Markdown标记（##、*、**、-、>、```、[]()等）
2. 删除所有emoji和装饰性符号（如😀、★、●、→、▪等）
3. 将标题转换为公文层级格式：
   - 一级标题使用：一、二、三、四、五、六、七、八、九、十...
   - 二级标题使用：（一）（二）（三）...
   - 三级标题使用：1. 2. 3. ...
   - 四级标题使用：（1）（2）（3）...
4. 合理划分段落，每个完整意思为一段
5. 保持原文内容不变，不增加、不删减、不润色、不改变原意
6. 保留原有的段落换行结构

请直接输出规范化后的纯文本，不要添加任何解释、说明或标记。"""

    @property
    def name(self) -> str:
        return "CleanerAgent"

    def get_prompt(self, text: str, issues: List[str] = None) -> str:
        """构建清洗prompt"""
        issues_str = "\n".join(f"- {issue}" for issue in (issues or ["需要整体规范化"]))

        return self.PROMPT_TEMPLATE.format(
            text=text,
            issues=issues_str
        )

    def parse_response(self, content: str) -> CleanerResult:
        """解析LLM响应"""
        # CleanerAgent返回的是纯文本，不是JSON
        # 需要清理可能的多余内容

        cleaned_text = content.strip()

        # 移除可能的开头解释
        prefixes_to_remove = [
            "以下是规范化后的文本：",
            "以下是规范化后的内容：",
            "规范化后的文本：",
            "规范化后的内容：",
            "规范化结果：",
        ]
        for prefix in prefixes_to_remove:
            if cleaned_text.startswith(prefix):
                cleaned_text = cleaned_text[len(prefix):].strip()

        # 移除可能的代码块包装
        if cleaned_text.startswith("```") and cleaned_text.endswith("```"):
            lines = cleaned_text.split("\n")
            if len(lines) > 2:
                cleaned_text = "\n".join(lines[1:-1])

        if not cleaned_text:
            return CleanerResult(
                success=False,
                cleaned_text="",
                error="清洗后文本为空"
            )

        logger.info(f"[{self.name}] 清洗完成，原文{len(content)}字 → 清洗后{len(cleaned_text)}字")

        return CleanerResult(
            success=True,
            cleaned_text=cleaned_text,
            changes_made=["已完成文本规范化"]
        )

    def clean(self, text: str, issues: List[str] = None) -> str:
        """
        清洗文本

        Args:
            text: 待清洗的文本
            issues: RouterAgent发现的问题列表

        Returns:
            str: 清洗后的文本（如果失败则返回原文）
        """
        result = self.execute(text, issues)

        if result.success and result.cleaned_text:
            return result.cleaned_text
        else:
            logger.warning(f"[{self.name}] 清洗失败，返回原文")
            return text
