"""
AgentOrchestrator - Agent编排器

负责协调各个Agent的调用流程，实现完整的公文处理管道
"""
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from app.core.agents.base_agent import AgentResult
from app.core.agents.router_agent import RouterAgent, RouterResult
from app.core.agents.cleaner_agent import CleanerAgent, CleanerResult
from app.core.agents.marker_agent import MarkerAgent, AnalysisResult
from app.core.agents.validator_agent import ValidatorAgent, ValidatorResult

logger = logging.getLogger(__name__)

# 进度回调类型
ProgressCallback = Callable[[str, str], None]


@dataclass
class ProcessResult(AgentResult):
    """完整处理流程的结果"""
    analysis_result: Optional[AnalysisResult] = None  # 最终分析结果
    was_cleaned: bool = False                          # 是否经过文本清洗
    router_confidence: float = 0.0                     # 原始规范性置信度
    retry_count: int = 0                               # 重试次数
    issues_fixed: List[str] = field(default_factory=list)  # 修复的问题列表
    validation_issues: List[str] = field(default_factory=list)  # 校验发现的问题


class AgentOrchestrator:
    """
    Agent编排器

    协调以下Agent的调用流程：
    1. RouterAgent: 判断文本是否符合公文规范
    2. CleanerAgent: 清洗不规范的文本（条件调用）
    3. MarkerAgent: 识别文档结构
    4. ValidatorAgent: 校验分析结果（带重试机制）
    """

    # 置信度阈值，低于此值需要清洗
    CONFIDENCE_THRESHOLD = 0.85

    # 最大重试次数
    MAX_RETRIES = 2

    def __init__(self, model: str = None):
        """
        初始化编排器

        Args:
            model: LLM模型名称，传递给各Agent
        """
        self.router = RouterAgent(model=model)
        self.cleaner = CleanerAgent(model=model)
        self.marker = MarkerAgent(model=model)
        self.validator = ValidatorAgent(model=model)

    def process(
        self,
        text: str,
        progress_callback: Optional[ProgressCallback] = None
    ) -> ProcessResult:
        """
        执行完整的公文处理流程

        Args:
            text: 待处理的文本
            progress_callback: 进度回调函数，格式为 callback(stage, message)
                stage: 阶段标识 (analyzing, cleaning, marking, validating, completed)
                message: 显示给用户的消息

        Returns:
            ProcessResult: 处理结果
        """
        logger.info("=" * 50)
        logger.info("开始公文处理流程")
        logger.info("=" * 50)

        # Step 1: 路由判断
        self._notify_progress(progress_callback, "analyzing", "正在分析文本规范性...")
        router_result = self._step_router(text)

        if not router_result.success:
            return ProcessResult(
                success=False,
                error=f"规范性判断失败: {router_result.error}",
                router_confidence=0.0
            )

        # Step 2: 条件清洗
        processed_text = text
        was_cleaned = False
        issues_fixed = []

        needs_cleaning = (
            not router_result.is_official_style or
            router_result.confidence < self.CONFIDENCE_THRESHOLD
        )

        if needs_cleaning:
            self._notify_progress(progress_callback, "cleaning", "正在规范化文本格式...")
            clean_result = self._step_cleaner(text, router_result.issues)

            if clean_result.cleaned_text:
                processed_text = clean_result.cleaned_text
                was_cleaned = True
                issues_fixed = router_result.issues.copy()
                logger.info(f"文本已清洗，处理了 {len(issues_fixed)} 个问题")
        else:
            logger.info(f"文本已符合公文规范 (置信度: {router_result.confidence:.2f})，跳过清洗")

        # Step 3 & 4: 结构标记 + 校验（带重试）
        retry_count = 0
        current_text = processed_text
        analysis_result = None
        validator_result = None

        while retry_count <= self.MAX_RETRIES:
            # Step 3: 结构标记
            retry_suffix = f"（第{retry_count}次重试）" if retry_count > 0 else ""
            self._notify_progress(
                progress_callback,
                "marking",
                f"正在识别文档结构...{retry_suffix}"
            )

            analysis_result = self._step_marker(current_text)

            if not analysis_result.success:
                return ProcessResult(
                    success=False,
                    error=f"结构识别失败: {analysis_result.error_message}",
                    was_cleaned=was_cleaned,
                    router_confidence=router_result.confidence,
                    retry_count=retry_count
                )

            # Step 4: 一致性校验
            self._notify_progress(
                progress_callback,
                "validating",
                f"正在校验结果...{retry_suffix}"
            )

            validator_result = self._step_validator(analysis_result)

            if validator_result.is_valid:
                logger.info("校验通过！")
                break

            # 校验失败，需要重试
            retry_count += 1
            if retry_count <= self.MAX_RETRIES:
                logger.warning(f"校验未通过，准备第 {retry_count} 次重试")
                logger.warning(f"问题: {validator_result.issues}")

                # 从Agent 2重新开始：重新清洗
                self._notify_progress(
                    progress_callback,
                    "cleaning",
                    f"正在重新规范化文本...（第{retry_count}次重试）"
                )

                # 使用校验发现的问题指导清洗
                combined_issues = router_result.issues + validator_result.issues
                clean_result = self._step_cleaner(current_text, combined_issues)

                if clean_result.cleaned_text:
                    current_text = clean_result.cleaned_text
                    was_cleaned = True
                    issues_fixed.extend(validator_result.issues)

        # 判断最终结果
        if not validator_result.is_valid:
            logger.error(f"处理失败：重试 {self.MAX_RETRIES} 次后仍未通过校验")
            return ProcessResult(
                success=False,
                error="原文结构不适合自动排版，请手动调整后重试",
                analysis_result=analysis_result,
                was_cleaned=was_cleaned,
                router_confidence=router_result.confidence,
                retry_count=retry_count,
                issues_fixed=issues_fixed,
                validation_issues=validator_result.issues
            )

        # 处理成功
        self._notify_progress(progress_callback, "completed", "处理完成！")

        logger.info("=" * 50)
        logger.info("公文处理流程完成")
        logger.info(f"- 是否清洗: {was_cleaned}")
        logger.info(f"- 原始置信度: {router_result.confidence:.2f}")
        logger.info(f"- 重试次数: {retry_count}")
        logger.info(f"- 识别元素数: {len(analysis_result.elements)}")
        logger.info("=" * 50)

        return ProcessResult(
            success=True,
            analysis_result=analysis_result,
            was_cleaned=was_cleaned,
            router_confidence=router_result.confidence,
            retry_count=retry_count,
            issues_fixed=issues_fixed
        )

    def _step_router(self, text: str) -> RouterResult:
        """Step 1: 调用RouterAgent判断文本规范性"""
        logger.info("[Step 1] 调用 RouterAgent 判断文本规范性")
        return self.router.analyze(text)

    def _step_cleaner(self, text: str, issues: List[str]) -> CleanerResult:
        """Step 2: 调用CleanerAgent清洗文本"""
        logger.info(f"[Step 2] 调用 CleanerAgent 清洗文本，需处理问题: {len(issues)} 个")
        result = self.cleaner.execute(text, issues)
        if isinstance(result, CleanerResult):
            return result
        # 如果返回的是基类，转换一下
        return CleanerResult(
            success=result.success,
            cleaned_text=text if not result.success else "",
            error=result.error
        )

    def _step_marker(self, text: str) -> AnalysisResult:
        """Step 3: 调用MarkerAgent识别文档结构"""
        logger.info("[Step 3] 调用 MarkerAgent 识别文档结构")

        # 将文本转换为带编号的格式
        lines = text.strip().split('\n')
        numbered_text = '\n'.join(f"[{i}] {line}" for i, line in enumerate(lines) if line.strip())

        return self.marker.analyze(numbered_text)

    def _step_validator(self, analysis_result: AnalysisResult) -> ValidatorResult:
        """Step 4: 调用ValidatorAgent校验分析结果"""
        logger.info("[Step 4] 调用 ValidatorAgent 校验分析结果")
        return self.validator.validate(analysis_result)

    def _notify_progress(
        self,
        callback: Optional[ProgressCallback],
        stage: str,
        message: str
    ):
        """通知进度更新"""
        logger.info(f"[进度] {stage}: {message}")
        if callback:
            try:
                callback(stage, message)
            except Exception as e:
                logger.warning(f"进度回调执行失败: {e}")
