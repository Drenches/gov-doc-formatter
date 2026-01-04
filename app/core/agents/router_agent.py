"""
RouterAgent - 轻量过滤器

职责退化：只做两件事
1. 判断是否"明显不是公文"（聊天、论文、代码等）
2. 判断是否存在必须先清洗的噪声（emoji/markdown/项目符号等）

不再做"文体分类"，不再决定"走哪条结构路径"
"""
import logging
from dataclasses import dataclass, field
from typing import List

from app.core.agents.base_agent import BaseAgent, AgentResult

logger = logging.getLogger(__name__)


@dataclass
class RouterResult(AgentResult):
    """路由判断结果"""
    is_likely_official: bool = True       # 是否可能是公文（非明显非公文）
    needs_cleaning: bool = False           # 是否需要先清洗
    noise_issues: List[str] = field(default_factory=list)  # 发现的噪声问题


class RouterAgent(BaseAgent):
    """
    轻量过滤器Agent

    核心理念：
    - 不做文体分类（声明/通知/规定等）
    - 不决定"走哪条结构路径"
    - 只回答两个问题：
      1. 这是不是"明显不是公文"？
      2. 是否存在必须先清洗的噪声？

    让 Marker 自己决定如何排版
    """

    PROMPT_TEMPLATE = """你是公文格式预处理专家。请快速判断以下文本的预处理需求。

【任务】只需要回答两个问题：

1. 这是否"明显不是公文"？
   - 明显不是公文：聊天记录、代码、论文摘要、小说、新闻稿、广告文案
   - 可能是公文：有标题、有正文段落、像是某种官方/正式文档
   - 注意：即使格式不完美，只要"像是公文"就不算"明显不是"

2. 是否存在需要清洗的噪声？
   - Markdown标记（##、**、*、-、>、```等）
   - emoji或装饰符号（✅❌📌🎯等）
   - 网页残留（链接、HTML标签）
   - 奇怪的项目符号（•、►、◆等）

文本内容：
{text}

请以JSON格式返回：
{{
  "is_likely_official": true或false,
  "needs_cleaning": true或false,
  "noise_issues": ["问题1", "问题2"]
}}

判断原则：
- 宁可误判为"可能是公文"，也不要误判为"明显不是"
- noise_issues 只列出实际发现的噪声问题
- 没有发现噪声就返回空列表"""

    @property
    def name(self) -> str:
        return "RouterAgent"

    def get_prompt(self, text: str) -> str:
        """构建判断prompt"""
        # 限制文本长度，只看前面部分即可判断
        max_length = 3000
        if len(text) > max_length:
            text = text[:max_length] + "\n...(文本已截断)"

        return self.PROMPT_TEMPLATE.format(text=text)

    def parse_response(self, content: str) -> RouterResult:
        """解析LLM响应"""
        json_data = self.extract_json(content)

        if not json_data:
            logger.warning(f"[{self.name}] 无法解析JSON响应，默认为可能是公文")
            return RouterResult(
                success=True,
                is_likely_official=True,  # 默认认为是公文
                needs_cleaning=False,
                noise_issues=[]
            )

        try:
            is_likely_official = json_data.get('is_likely_official', True)
            needs_cleaning = json_data.get('needs_cleaning', False)
            noise_issues = json_data.get('noise_issues', [])

            # 确保noise_issues是列表
            if not isinstance(noise_issues, list):
                noise_issues = [str(noise_issues)] if noise_issues else []

            logger.info(
                f"[{self.name}] 判断结果: is_likely_official={is_likely_official}, "
                f"needs_cleaning={needs_cleaning}, noise_issues={len(noise_issues)}个"
            )

            return RouterResult(
                success=True,
                is_likely_official=is_likely_official,
                needs_cleaning=needs_cleaning,
                noise_issues=noise_issues
            )

        except Exception as e:
            logger.error(f"[{self.name}] 解析结果异常: {str(e)}")
            return RouterResult(
                success=True,
                is_likely_official=True,  # 出错时默认为可能是公文
                needs_cleaning=False,
                noise_issues=[],
                error=str(e)
            )

    def analyze(self, text: str) -> RouterResult:
        """
        分析文本，判断是否需要预处理

        Args:
            text: 待分析的文本

        Returns:
            RouterResult: 判断结果
        """
        return self.execute(text)
