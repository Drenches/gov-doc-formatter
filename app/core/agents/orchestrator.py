"""
AgentOrchestrator - Agent编排器

新流程：
1. Router: 轻量过滤（是否明显非公文、是否需要清洗）
2. Cleaner: 条件清洗（保守/重度两档）
3. Marker: 排版规划（安全排版优先）
4. Validator: 硬约束校验（程序化）

核心改进：去掉显式文体分类，让 Marker 自己判断如何排版
"""
import logging
from dataclasses import dataclass, field
from typing import Callable, List, Optional

from app.core.agents.base_agent import AgentResult
from app.core.agents.router_agent import RouterAgent, RouterResult
from app.core.agents.cleaner_agent import CleanerAgent, CleanerResult, CleaningMode
from app.core.agents.marker_agent import MarkerAgent, LayoutResult
from app.core.agents.validator_agent import ValidatorAgent, ValidatorResult

logger = logging.getLogger(__name__)

# 进度回调类型
ProgressCallback = Callable[[str, str], None]


@dataclass
class ProcessResult(AgentResult):
    """完整处理流程的结果"""
    layout_result: Optional[LayoutResult] = None   # 排版规划结果
    was_cleaned: bool = False                       # 是否经过文本清洗
    cleaning_mode: Optional[str] = None             # 使用的清洗模式
    retry_count: int = 0                            # 重试次数
    issues_fixed: List[str] = field(default_factory=list)   # 修复的问题列表
    validation_warnings: List[str] = field(default_factory=list)  # 校验警告

    # 向后兼容的别名
    @property
    def analysis_result(self):
        return self.layout_result


class AgentOrchestrator:
    """
    Agent编排器

    新流程：
    1. RouterAgent: 轻量过滤
       - 判断是否"明显不是公文"
       - 判断是否需要清洗

    2. CleanerAgent: 条件清洗
       - 需要清洗时才调用
       - 根据情况选择保守/重度模式

    3. MarkerAgent: 排版规划
       - 不依赖预分类
       - 自主判断合法结构
       - 安全排版优先

    4. ValidatorAgent: 硬约束校验
       - 程序化校验，不调用 LLM
       - 只检查"绝对不能接受"的问题
    """

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
                stage: 阶段标识 (filtering, cleaning, planning, validating, completed)
                message: 显示给用户的消息

        Returns:
            ProcessResult: 处理结果
        """
        logger.info("=" * 50)
        logger.info("开始公文处理流程")
        logger.info("=" * 50)

        # Step 1: 轻量过滤
        self._notify_progress(progress_callback, "filtering", "正在分析文档...")
        router_result = self._step_router(text)

        if not router_result.success:
            return ProcessResult(
                success=False,
                error=f"文档分析失败: {router_result.error}"
            )

        # 检查是否明显不是公文
        if not router_result.is_likely_official:
            logger.warning("文档被判定为明显不是公文")
            return ProcessResult(
                success=False,
                error="输入内容不像是公文格式，请检查后重试"
            )

        # Step 2: 条件清洗
        processed_text = text
        was_cleaned = False
        cleaning_mode = None
        issues_fixed = []

        if router_result.needs_cleaning:
            self._notify_progress(progress_callback, "cleaning", "正在清洗文本格式...")

            # 默认使用重度清洗模式
            mode = CleaningMode.DEEP
            cleaning_mode = mode.value

            clean_result = self._step_cleaner(text, router_result.noise_issues, mode)

            if clean_result.success and clean_result.cleaned_text:
                processed_text = clean_result.cleaned_text
                was_cleaned = True
                issues_fixed = router_result.noise_issues.copy()
                logger.info(f"文本已清洗（{mode.value}模式），处理了 {len(issues_fixed)} 个问题")
        else:
            logger.info("文本无需清洗，直接进入排版规划")

        # Step 3 & 4: 排版规划 + 校验（带重试）
        retry_count = 0
        current_text = processed_text
        layout_result = None
        validator_result = None

        while retry_count <= self.MAX_RETRIES:
            # Step 3: 排版规划
            retry_suffix = f"（第{retry_count}次重试）" if retry_count > 0 else ""
            self._notify_progress(
                progress_callback,
                "planning",
                f"正在规划文档排版...{retry_suffix}"
            )

            layout_result = self._step_marker(current_text)

            if not layout_result.success:
                # 使用保守兜底排版
                logger.warning("排版规划失败，使用保守兜底方案")
                lines = current_text.strip().split('\n')
                layout_result = self.marker.fallback_layout(lines)

            # Step 4: 硬约束校验
            self._notify_progress(
                progress_callback,
                "validating",
                f"正在校验排版结果...{retry_suffix}"
            )

            validator_result = self._step_validator(layout_result)

            if validator_result.is_valid:
                logger.info("校验通过！")
                break

            # 校验失败，需要重试
            retry_count += 1
            if retry_count <= self.MAX_RETRIES:
                logger.warning(f"校验未通过，准备第 {retry_count} 次重试")
                logger.warning(f"问题: {validator_result.issues}")

                # 重新清洗（使用重度模式）
                self._notify_progress(
                    progress_callback,
                    "cleaning",
                    f"正在重新清洗文本...（第{retry_count}次重试）"
                )

                combined_issues = router_result.noise_issues + validator_result.issues
                clean_result = self._step_cleaner(
                    current_text, combined_issues, CleaningMode.DEEP
                )

                if clean_result.success and clean_result.cleaned_text:
                    current_text = clean_result.cleaned_text
                    was_cleaned = True
                    cleaning_mode = CleaningMode.DEEP.value
                    issues_fixed.extend(validator_result.issues)

        # 判断最终结果
        if not validator_result.is_valid:
            logger.error(f"处理失败：重试 {self.MAX_RETRIES} 次后仍未通过校验")
            return ProcessResult(
                success=False,
                error="文档结构不适合自动排版，请手动调整后重试",
                layout_result=layout_result,
                was_cleaned=was_cleaned,
                cleaning_mode=cleaning_mode,
                retry_count=retry_count,
                issues_fixed=issues_fixed,
                validation_warnings=validator_result.warnings
            )

        # 处理成功
        self._notify_progress(progress_callback, "completed", "处理完成！")

        logger.info("=" * 50)
        logger.info("公文处理流程完成")
        logger.info(f"- 是否清洗: {was_cleaned}")
        if was_cleaned:
            logger.info(f"- 清洗模式: {cleaning_mode}")
        logger.info(f"- 重试次数: {retry_count}")
        logger.info(f"- 识别元素数: {len(layout_result.elements)}")
        if validator_result.warnings:
            logger.info(f"- 警告数: {len(validator_result.warnings)}")
        logger.info("=" * 50)

        return ProcessResult(
            success=True,
            layout_result=layout_result,
            was_cleaned=was_cleaned,
            cleaning_mode=cleaning_mode,
            retry_count=retry_count,
            issues_fixed=issues_fixed,
            validation_warnings=validator_result.warnings
        )

    def _step_router(self, text: str) -> RouterResult:
        """Step 1: 调用RouterAgent进行轻量过滤"""
        logger.info("[Step 1] 调用 RouterAgent 轻量过滤")
        return self.router.analyze(text)

    def _step_cleaner(self, text: str, issues: List[str],
                      mode: CleaningMode) -> CleanerResult:
        """Step 2: 调用CleanerAgent清洗文本"""
        logger.info(f"[Step 2] 调用 CleanerAgent 清洗文本 (模式: {mode.value})")
        result = self.cleaner.execute(text, issues, mode)
        if isinstance(result, CleanerResult):
            return result
        # 如果返回的是基类，转换一下
        return CleanerResult(
            success=result.success,
            cleaned_text=text if not result.success else "",
            error=result.error
        )

    def _step_marker(self, text: str) -> LayoutResult:
        """Step 3: 调用MarkerAgent进行排版规划"""
        logger.info("[Step 3] 调用 MarkerAgent 排版规划")

        # 将文本转换为带编号的格式
        lines = text.strip().split('\n')
        numbered_text = '\n'.join(
            f"[{i}] {line}" for i, line in enumerate(lines) if line.strip()
        )

        return self.marker.analyze(numbered_text)

    def _step_validator(self, layout_result: LayoutResult) -> ValidatorResult:
        """Step 4: 调用ValidatorAgent进行硬约束校验"""
        logger.info("[Step 4] 调用 ValidatorAgent 硬约束校验")
        return self.validator.validate(layout_result)

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
