"""
RouterAgent - 行文规范性判断Agent

负责判断输入文本是否已经符合公文行文规范
"""
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from app.core.agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


@dataclass
class RouterResult(AgentResult):
    """路由判断结果"""
    is_official_style: bool = False
    confidence: float = 0.0
    issues: List[str] = field(default_factory=list)


class RouterAgent(BaseAgent):
    """
    行文规范性判断Agent

    判断文本是否已基本符合党政机关公文的行文结构
    """

    PROMPT_TEMPLATE = """你是公文格式判断专家。请判断以下文本是否已基本符合党政机关公文的行文结构。

判断标准：
1. 是否使用公文标题层级编号（如"一、""（一）""1.""（1）"）
2. 是否存在Markdown标记（如##、*、-、>、```等）
3. 是否存在emoji或特殊装饰符号（如★、●、→、😀等）
4. 段落结构是否清晰（非口语化、非碎片化）
5. 是否有明显的公文要素（标题、正文、落款等）

文本内容：
{text}

请严格以JSON格式返回判断结果，不要添加任何其他内容：
{{
  "is_official_style": true或false,
  "confidence": 0.0到1.0之间的数值,
  "issues": ["发现的问题1", "发现的问题2"]
}}

说明：
- is_official_style: 文本是否基本符合公文格式
- confidence: 判断的置信度（1.0表示完全确定）
- issues: 如果不符合，列出具体问题（如"存在Markdown标记##"、"包含emoji符号"等）"""

    @property
    def name(self) -> str:
        return "RouterAgent"

    def get_prompt(self, text: str) -> str:
        """构建判断prompt"""
        # 限制文本长度，避免token过多
        max_length = 8000
        if len(text) > max_length:
            text = text[:max_length] + "\n...(文本已截断)"

        return self.PROMPT_TEMPLATE.format(text=text)

    def parse_response(self, content: str) -> RouterResult:
        """解析LLM响应"""
        json_data = self.extract_json(content)

        if not json_data:
            logger.warning(f"[{self.name}] 无法解析JSON响应，使用默认值")
            return RouterResult(
                success=False,
                is_official_style=False,
                confidence=0.0,
                issues=["无法解析LLM响应"],
                error="JSON解析失败"
            )

        try:
            is_official = json_data.get('is_official_style', False)
            confidence = float(json_data.get('confidence', 0.0))
            issues = json_data.get('issues', [])

            # 确保confidence在有效范围内
            confidence = max(0.0, min(1.0, confidence))

            # 确保issues是列表
            if not isinstance(issues, list):
                issues = [str(issues)] if issues else []

            logger.info(f"[{self.name}] 判断结果: is_official={is_official}, confidence={confidence:.2f}, issues={len(issues)}个")

            return RouterResult(
                success=True,
                is_official_style=is_official,
                confidence=confidence,
                issues=issues
            )

        except Exception as e:
            logger.error(f"[{self.name}] 解析结果异常: {str(e)}")
            return RouterResult(
                success=False,
                is_official_style=False,
                confidence=0.0,
                issues=["解析结果时发生错误"],
                error=str(e)
            )

    def analyze(self, text: str) -> RouterResult:
        """
        分析文本是否符合公文规范

        Args:
            text: 待分析的文本

        Returns:
            RouterResult: 判断结果
        """
        return self.execute(text)
