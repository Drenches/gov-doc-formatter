"""
CleanerAgent - 文本清洗Agent

支持两档清洗模式：
1. 保守清洗（light）：只删噪声，不改结构
2. 重度清洗（deep）：可以适度整理段落结构

核心原则：不改变文字内容，只做格式清理
"""
import logging
from dataclasses import dataclass, field
from typing import List
from enum import Enum

from app.core.agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


class CleaningMode(str, Enum):
    """清洗模式"""
    LIGHT = "light"  # 保守清洗：只删噪声
    DEEP = "deep"    # 重度清洗：可整理结构


@dataclass
class CleanerResult(AgentResult):
    """清洗结果"""
    cleaned_text: str = ""
    changes_made: List[str] = field(default_factory=list)
    mode_used: CleaningMode = CleaningMode.LIGHT


class CleanerAgent(BaseAgent):
    """
    文本清洗Agent

    两档模式：
    - LIGHT（保守）：只删 emoji/markdown/装饰符号，不改段落
    - DEEP（重度）：可以整理明显的结构问题，但仍不引入强层级

    核心红线：
    - ❌ 不改变文字内容
    - ❌ 不增加、不删减、不润色
    - ❌ 不强行添加"一、（一）"等层级编号
    """

    # 保守清洗模板
    LIGHT_PROMPT = """你是公文格式清洗专家。请对以下文本进行【保守清洗】。

需要处理的噪声问题：
{issues}

原始文本：
{text}

【保守清洗规则】
只做以下操作，其他一律不动：
1. 删除 Markdown 标记（##、**、*、-、>、```、[]()等）
2. 删除 emoji 和装饰符号（✅❌📌🎯•►◆等）
3. 删除 HTML 标签（如有）
4. 删除网页链接残留

【禁止操作】
❌ 不要改变段落结构
❌ 不要合并或拆分段落
❌ 不要添加任何编号（一、二、三等）
❌ 不要修改任何文字内容
❌ 不要润色或重新组织语言

请直接输出清洗后的文本，不要添加任何解释。"""

    # 重度清洗模板
    DEEP_PROMPT = """你是公文格式清洗专家。请对以下文本进行【重度清洗】。

需要处理的问题：
{issues}

原始文本：
{text}

【重度清洗规则】
1. 删除所有 Markdown 标记、emoji、装饰符号、HTML 标签
2. 可以适度整理段落：
   - 把明显的小标题单独成段
   - 把过长的连续文本按语义合理分段
   - 整理混乱的换行

【禁止操作】
❌ 不要修改任何文字内容
❌ 不要增加或删除实质信息
❌ 不要强行添加"一、（一）1.（1）"等层级编号
❌ 不要把普通段落改造成标题
❌ 不要润色或重新组织语言

【重要】保持原文的结构特征：
- 如果原文没有层级标题，清洗后也不应有
- 如果原文是连续正文，保持连续正文的特征
- 只做"清理"，不做"美化"

请直接输出清洗后的文本，不要添加任何解释。"""

    @property
    def name(self) -> str:
        return "CleanerAgent"

    def get_prompt(self, text: str, issues: List[str] = None,
                   mode: CleaningMode = CleaningMode.LIGHT) -> str:
        """
        根据清洗模式构建prompt

        Args:
            text: 待清洗的文本
            issues: 需要处理的问题列表
            mode: 清洗模式（LIGHT/DEEP）
        """
        issues_str = "\n".join(f"- {issue}" for issue in (issues or ["需要整体规范化"]))

        if mode == CleaningMode.DEEP:
            return self.DEEP_PROMPT.format(text=text, issues=issues_str)
        else:
            return self.LIGHT_PROMPT.format(text=text, issues=issues_str)

    def parse_response(self, content: str) -> CleanerResult:
        """解析LLM响应"""
        cleaned_text = content.strip()

        # 移除可能的开头解释
        prefixes_to_remove = [
            "以下是规范化后的文本：",
            "以下是规范化后的内容：",
            "以下是清洗后的文本：",
            "以下是清洗后的内容：",
            "规范化后的文本：",
            "规范化后的内容：",
            "清洗后的文本：",
            "清洗后的内容：",
            "规范化结果：",
            "清洗结果：",
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
            changes_made=["已完成文本清洗"]
        )

    def clean(self, text: str, issues: List[str] = None,
              mode: CleaningMode = CleaningMode.LIGHT) -> str:
        """
        清洗文本

        Args:
            text: 待清洗的文本
            issues: 发现的噪声问题列表
            mode: 清洗模式（LIGHT 保守 / DEEP 重度）

        Returns:
            str: 清洗后的文本（如果失败则返回原文）
        """
        logger.info(f"[{self.name}] 使用 {mode.value} 模式清洗")

        result = self.execute(text, issues, mode)

        if isinstance(result, CleanerResult):
            result.mode_used = mode

        if result.success and hasattr(result, 'cleaned_text') and result.cleaned_text:
            return result.cleaned_text
        else:
            logger.warning(f"[{self.name}] 清洗失败，返回原文")
            return text
