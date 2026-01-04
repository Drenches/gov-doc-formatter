"""
ValidatorAgent - 硬约束校验器

核心理念：
- 让 LLM 决定"可能的最好排版"
- 让程序决定"什么排版绝对不能接受"

校验规则全部程序化，不再依赖 LLM 判断
"""
import logging
import re
from dataclasses import dataclass, field
from typing import List

from app.core.agents.base_agent import AgentResult
from app.core.agents.marker_agent import LayoutResult
from app.core.styles import ElementType

logger = logging.getLogger(__name__)


@dataclass
class ValidatorResult(AgentResult):
    """校验结果"""
    is_valid: bool = False
    issues: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)  # 警告（不影响通过）


class ValidatorAgent:
    """
    硬约束校验器

    核心原则：
    - 所有校验规则程序化，不调用 LLM
    - 只检查"绝对不能接受"的问题
    - 宽松校验，减少误判

    校验规则分两类：
    1. 硬约束（会导致校验失败）
       - 没有任何元素
       - 存在严重的结构错误

    2. 软约束（只产生警告）
       - 缺少标题
       - 缺少落款
       - 层级跳跃
    """

    def __init__(self, model: str = None):
        """初始化（保持接口兼容，但不使用 model）"""
        self.name = "ValidatorAgent"

    def validate(self, layout_result: LayoutResult) -> ValidatorResult:
        """
        校验排版结果

        Args:
            layout_result: MarkerAgent 的排版规划结果

        Returns:
            ValidatorResult: 校验结果
        """
        logger.info(f"[{self.name}] 开始校验排版结果")

        issues = []      # 硬约束问题（会导致失败）
        warnings = []    # 软约束问题（只是警告）

        # 检查基本有效性
        if not layout_result.success:
            issues.append("排版规划失败")
            return ValidatorResult(
                success=True,
                is_valid=False,
                issues=issues,
                warnings=warnings
            )

        if not layout_result.elements:
            issues.append("没有识别到任何文档元素")
            return ValidatorResult(
                success=True,
                is_valid=False,
                issues=issues,
                warnings=warnings
            )

        # 执行各项检查
        self._check_title(layout_result, warnings)
        self._check_heading_levels(layout_result, warnings)
        self._check_markdown_residue(layout_result, issues)
        self._check_element_coverage(layout_result, warnings)

        # 判断是否通过
        is_valid = len(issues) == 0

        if is_valid:
            logger.info(f"[{self.name}] 校验通过，警告数: {len(warnings)}")
        else:
            logger.warning(f"[{self.name}] 校验失败，问题数: {len(issues)}")

        return ValidatorResult(
            success=True,
            is_valid=is_valid,
            issues=issues,
            warnings=warnings
        )

    def _check_title(self, layout_result: LayoutResult, warnings: List[str]):
        """检查是否有标题（软约束）"""
        has_title = any(
            e.element_type == ElementType.TITLE
            for e in layout_result.elements
        )
        if not has_title:
            warnings.append("未识别到公文标题")

    def _check_heading_levels(self, layout_result: LayoutResult, warnings: List[str]):
        """
        检查标题层级（软约束）

        规则：允许没有任何 heading，但如果有 heading，层级不应跳跃
        例如：有 heading2 但没有 heading1 是警告（不是错误）
        """
        heading_levels = []
        for elem in layout_result.elements:
            if elem.element_type.startswith("heading"):
                try:
                    level = int(elem.element_type[-1])
                    heading_levels.append(level)
                except ValueError:
                    pass

        if not heading_levels:
            # 没有任何 heading 是完全合法的
            return

        # 检查层级跳跃
        min_level = min(heading_levels)
        if min_level > 1:
            # 例如：最小层级是 heading2，没有 heading1
            # 这可能是合法的（如只有数字编号的文档）
            warnings.append(f"标题层级从 {min_level} 级开始，没有更高层级")

        # 检查层级连续性
        for i in range(1, len(heading_levels)):
            prev_level = heading_levels[i - 1]
            curr_level = heading_levels[i]
            if curr_level > prev_level + 1:
                warnings.append(
                    f"标题层级从 {prev_level} 级跳跃到 {curr_level} 级"
                )

    def _check_markdown_residue(self, layout_result: LayoutResult, issues: List[str]):
        """
        检查 Markdown 残留（硬约束）

        如果内容中还有明显的 Markdown 标记，说明清洗不彻底
        """
        # 严重的 Markdown 标记（会导致失败）
        severe_patterns = [
            (r'^#{1,6}\s', 'Markdown 标题标记 (#)'),
            (r'```', '代码块标记 (```)'),
        ]

        # 轻微的 Markdown 标记（只是警告，不再检查）
        # 因为 ** 可能是强调，- 可能是列表，这些不一定是问题

        for elem in layout_result.elements:
            content = elem.content
            for pattern, desc in severe_patterns:
                if re.search(pattern, content, re.MULTILINE):
                    issues.append(f"内容中存在 {desc}")
                    return  # 发现一个就够了

    def _check_element_coverage(self, layout_result: LayoutResult, warnings: List[str]):
        """
        检查元素覆盖度（软约束）

        检查是否所有段落都被标记了
        """
        indices = [e.index for e in layout_result.elements]
        if indices:
            max_index = max(indices)
            expected_count = max_index + 1
            actual_count = len(indices)

            if actual_count < expected_count * 0.8:
                # 如果标记的元素少于预期的 80%，可能有遗漏
                warnings.append(
                    f"可能存在段落遗漏：预期 {expected_count} 个，实际 {actual_count} 个"
                )
