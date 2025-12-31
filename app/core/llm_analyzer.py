"""
LLM分析模块 - 使用通义千问分析公文结构

此模块已重构，现在作为 AgentOrchestrator 的兼容层。
实际的分析逻辑由 Multi-Agent 系统处理。
"""
import logging
from typing import Optional

from app.core.agents import (
    AgentOrchestrator,
    ProcessResult,
    AnalysisResult,
    DocumentElement
)

logger = logging.getLogger(__name__)

# 导出数据类，保持向后兼容
__all__ = ['LLMAnalyzer', 'AnalysisResult', 'DocumentElement', 'analyze_document']


class LLMAnalyzer:
    """
    使用通义千问分析公文结构

    此类现在是 AgentOrchestrator 的包装器，提供向后兼容的接口。
    内部使用 Multi-Agent 系统进行处理：
    1. RouterAgent: 判断文本规范性
    2. CleanerAgent: 清洗不规范文本（条件调用）
    3. MarkerAgent: 识别文档结构
    4. ValidatorAgent: 校验分析结果
    """

    def __init__(self, api_key: str = None, model: str = None):
        """
        初始化分析器

        Args:
            api_key: 通义千问API密钥（现已不使用，保留参数以兼容旧代码）
            model: 模型名称
        """
        self.orchestrator = AgentOrchestrator(model=model)
        self._last_process_result: Optional[ProcessResult] = None

    def analyze(self, document_text: str) -> AnalysisResult:
        """
        分析文档结构

        Args:
            document_text: 带段落编号的文档文本

        Returns:
            AnalysisResult: 分析结果
        """
        # 移除段落编号前缀（如果有），因为 Orchestrator 会重新添加
        clean_text = self._remove_line_numbers(document_text)

        # 调用编排器处理
        process_result = self.orchestrator.process(clean_text)

        # 保存处理结果，供外部获取详细信息
        self._last_process_result = process_result

        if process_result.success and process_result.analysis_result:
            return process_result.analysis_result
        else:
            # 构造失败的 AnalysisResult
            return AnalysisResult(
                success=False,
                error_message=process_result.error or "分析失败"
            )

    def get_last_process_info(self) -> Optional[dict]:
        """
        获取最近一次处理的详细信息

        Returns:
            dict: 包含处理过程信息的字典，包括：
                - was_cleaned: 是否经过文本清洗
                - router_confidence: 原始规范性置信度
                - retry_count: 重试次数
                - issues_fixed: 修复的问题列表
        """
        if not self._last_process_result:
            return None

        return {
            "was_cleaned": self._last_process_result.was_cleaned,
            "router_confidence": self._last_process_result.router_confidence,
            "retry_count": self._last_process_result.retry_count,
            "issues_fixed": self._last_process_result.issues_fixed,
            "validation_issues": self._last_process_result.validation_issues
        }

    def _remove_line_numbers(self, text: str) -> str:
        """
        移除行首的段落编号

        Args:
            text: 可能带有 [0] [1] 格式编号的文本

        Returns:
            str: 去除编号后的纯文本
        """
        lines = []
        for line in text.split('\n'):
            # 匹配 [数字] 开头的格式
            if line.strip().startswith('[') and ']' in line:
                bracket_end = line.index(']')
                # 检查方括号内是否为数字
                bracket_content = line[line.index('[') + 1:bracket_end].strip()
                if bracket_content.isdigit():
                    # 移除编号，保留后面的内容
                    line = line[bracket_end + 1:].strip()
            lines.append(line)
        return '\n'.join(lines)


def analyze_document(document_text: str, api_key: str = None) -> AnalysisResult:
    """
    便捷函数：分析文档

    Args:
        document_text: 文档文本
        api_key: API密钥（现已不使用，保留参数以兼容）

    Returns:
        AnalysisResult: 分析结果
    """
    analyzer = LLMAnalyzer(api_key=api_key)
    return analyzer.analyze(document_text)
