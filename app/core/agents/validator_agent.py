"""
ValidatorAgent - 一致性校验Agent

负责检查分析结果是否存在问题
"""
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.agents.base_agent import BaseAgent, AgentResult
from app.core.agents.marker_agent import AnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class ValidatorResult(AgentResult):
    """校验结果"""
    is_valid: bool = False
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ValidatorAgent(BaseAgent):
    """
    一致性校验Agent

    检查分析结果是否存在问题：
    - 标题层级是否闭合
    - 是否还有异常符号
    - 编号是否连续
    - 类型标记是否合理
    """

    PROMPT_TEMPLATE = """你是公文格式审核专家。请检查以下公文分析结果是否存在问题。

分析结果：
{analysis_json}

请检查以下方面：
1. 标题层级是否正确闭合（有一级标题才能有二级，有二级才能有三级）
2. 内容中是否还存在Markdown标记（##、*、-、>等）或异常符号（emoji等）
3. 标题编号是否连续（一、二、三...不应跳过编号）
4. 是否有明确的公文标题（title类型）
5. 内容类型标记是否合理（例如：很长的内容不应标记为标题）

请以JSON格式返回检查结果：
{{
  "is_valid": true或false,
  "issues": ["发现的问题1", "发现的问题2"],
  "suggestions": ["修改建议1", "修改建议2"]
}}

说明：
- is_valid: 分析结果是否可接受（没有严重问题）
- issues: 发现的问题列表
- suggestions: 修改建议列表

如果只有轻微问题（如缺少发文机关），仍可标记为is_valid=true。
只有存在严重问题（如层级错乱、大量异常符号）才标记为is_valid=false。"""

    @property
    def name(self) -> str:
        return "ValidatorAgent"

    def get_prompt(self, analysis_result: AnalysisResult) -> str:
        """构建校验prompt"""
        # 将分析结果转换为JSON字符串
        elements_data = []
        for elem in analysis_result.elements:
            elements_data.append({
                "index": elem.index,
                "type": elem.element_type,
                "content": elem.content[:100] + "..." if len(elem.content) > 100 else elem.content
            })

        analysis_json = json.dumps({
            "title": analysis_result.title,
            "issuing_authority": analysis_result.issuing_authority,
            "date": analysis_result.date,
            "elements": elements_data
        }, ensure_ascii=False, indent=2)

        return self.PROMPT_TEMPLATE.format(analysis_json=analysis_json)

    def parse_response(self, content: str) -> ValidatorResult:
        """解析LLM响应"""
        json_data = self.extract_json(content)

        if not json_data:
            logger.warning(f"[{self.name}] 无法解析JSON响应，默认通过")
            return ValidatorResult(
                success=True,
                is_valid=True,
                issues=["无法解析校验响应"],
                suggestions=[]
            )

        try:
            is_valid = json_data.get('is_valid', True)
            issues = json_data.get('issues', [])
            suggestions = json_data.get('suggestions', [])

            # 确保是列表
            if not isinstance(issues, list):
                issues = [str(issues)] if issues else []
            if not isinstance(suggestions, list):
                suggestions = [str(suggestions)] if suggestions else []

            logger.info(f"[{self.name}] 校验结果: is_valid={is_valid}, issues={len(issues)}个")

            return ValidatorResult(
                success=True,
                is_valid=is_valid,
                issues=issues,
                suggestions=suggestions
            )

        except Exception as e:
            logger.error(f"[{self.name}] 解析结果异常: {str(e)}")
            return ValidatorResult(
                success=True,
                is_valid=True,  # 解析失败时默认通过
                issues=[f"校验解析错误: {str(e)}"],
                suggestions=[]
            )

    def validate(self, analysis_result: AnalysisResult) -> ValidatorResult:
        """
        校验分析结果

        Args:
            analysis_result: MarkerAgent的分析结果

        Returns:
            ValidatorResult: 校验结果
        """
        # 先做基本的程序化校验
        basic_issues = self._basic_validation(analysis_result)

        # 如果基本校验发现严重问题，直接返回
        if basic_issues:
            logger.info(f"[{self.name}] 基本校验发现问题: {basic_issues}")

        # 调用LLM进行深度校验
        result = self.execute(analysis_result)

        # 合并基本校验的问题
        if isinstance(result, ValidatorResult) and basic_issues:
            result.issues = basic_issues + result.issues
            if basic_issues:
                result.is_valid = False

        return result

    def _basic_validation(self, analysis_result: AnalysisResult) -> List[str]:
        """
        基本程序化校验

        Returns:
            List[str]: 发现的问题列表
        """
        issues = []

        if not analysis_result.success:
            issues.append("分析结果标记为失败")
            return issues

        if not analysis_result.elements:
            issues.append("没有识别到任何文档元素")
            return issues

        # 检查是否有标题
        has_title = any(e.element_type == "title" for e in analysis_result.elements)
        if not has_title:
            issues.append("未识别到公文标题")

        # 检查标题层级
        heading_levels = []
        for elem in analysis_result.elements:
            if elem.element_type.startswith("heading"):
                try:
                    level = int(elem.element_type[-1])
                    heading_levels.append(level)
                except ValueError:
                    pass

        # 检查层级跳跃
        for i, level in enumerate(heading_levels):
            if i == 0 and level > 1:
                issues.append(f"标题层级从{level}级开始，应该从一级开始")
            elif i > 0:
                prev_level = heading_levels[i - 1]
                if level > prev_level + 1:
                    issues.append(f"标题层级从{prev_level}级跳跃到{level}级")

        # 检查内容中是否有Markdown标记
        markdown_patterns = ['##', '**', '__', '```', '- [', '* ', '> ']
        for elem in analysis_result.elements:
            for pattern in markdown_patterns:
                if pattern in elem.content:
                    issues.append(f"内容中存在Markdown标记: {pattern}")
                    break

        return issues
