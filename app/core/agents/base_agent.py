"""
Agent基类模块

定义所有Agent的抽象基类和通用功能
"""
import re
import json
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Optional
from dashscope import Generation

from app.config import DASHSCOPE_API_KEY, LLM_MODEL

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    """Agent执行结果的基类"""
    success: bool
    raw_response: str = ""
    error: Optional[str] = None


class BaseAgent(ABC):
    """
    Agent抽象基类

    所有Agent都继承此类，实现统一的LLM调用和结果解析接口
    """

    def __init__(self, model: str = None):
        self.model = model or LLM_MODEL
        self.api_key = DASHSCOPE_API_KEY

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent名称，用于日志和调试"""
        pass

    @abstractmethod
    def get_prompt(self, *args, **kwargs) -> str:
        """
        构建发送给LLM的prompt

        子类必须实现此方法
        """
        pass

    @abstractmethod
    def parse_response(self, content: str) -> AgentResult:
        """
        解析LLM返回的内容

        子类必须实现此方法
        """
        pass

    def call_llm(self, prompt: str) -> str:
        """
        调用LLM API

        Returns:
            str: LLM返回的文本内容

        Raises:
            Exception: API调用失败时抛出异常
        """
        logger.info(f"[{self.name}] 调用LLM...")
        logger.debug(f"[{self.name}] Prompt长度: {len(prompt)} 字符")

        try:
            response = Generation.call(
                model=self.model,
                prompt=prompt,
                result_format='message'
            )

            if response.status_code != 200:
                error_msg = f"API调用失败: {response.code} - {response.message}"
                logger.error(f"[{self.name}] {error_msg}")
                raise Exception(error_msg)

            content = response.output.choices[0].message.content
            logger.debug(f"[{self.name}] 响应长度: {len(content)} 字符")
            return content

        except Exception as e:
            logger.error(f"[{self.name}] LLM调用异常: {str(e)}")
            raise

    def extract_json(self, content: str) -> Optional[Dict]:
        """
        从LLM响应中提取JSON对象

        支持多种格式：
        1. ```json ... ```
        2. ``` ... ```
        3. 直接的 {...}
        """
        # 尝试提取 ```json ... ``` 格式
        json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试提取 ``` ... ``` 格式
        code_match = re.search(r'```\s*([\s\S]*?)\s*```', content)
        if code_match:
            try:
                return json.loads(code_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试直接解析JSON对象
        json_obj_match = re.search(r'\{[\s\S]*\}', content)
        if json_obj_match:
            try:
                return json.loads(json_obj_match.group())
            except json.JSONDecodeError:
                pass

        return None

    def execute(self, *args, **kwargs) -> AgentResult:
        """
        执行Agent的完整流程

        1. 构建prompt
        2. 调用LLM
        3. 解析响应
        """
        try:
            prompt = self.get_prompt(*args, **kwargs)
            response = self.call_llm(prompt)
            result = self.parse_response(response)
            result.raw_response = response
            return result
        except Exception as e:
            logger.error(f"[{self.name}] 执行失败: {str(e)}")
            return AgentResult(
                success=False,
                error=str(e)
            )
