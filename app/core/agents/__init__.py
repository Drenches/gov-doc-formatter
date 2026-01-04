"""
Agent模块

包含所有用于公文处理的Agent
"""
from app.core.agents.base_agent import BaseAgent, AgentResult
from app.core.agents.router_agent import RouterAgent, RouterResult
from app.core.agents.cleaner_agent import CleanerAgent, CleanerResult, CleaningMode
from app.core.agents.marker_agent import MarkerAgent, LayoutResult, AnalysisResult, DocumentElement
from app.core.agents.validator_agent import ValidatorAgent, ValidatorResult
from app.core.agents.orchestrator import AgentOrchestrator, ProcessResult

__all__ = [
    'BaseAgent',
    'AgentResult',
    'RouterAgent',
    'RouterResult',
    'CleanerAgent',
    'CleanerResult',
    'CleaningMode',
    'MarkerAgent',
    'LayoutResult',
    'AnalysisResult',  # 向后兼容的别名
    'DocumentElement',
    'ValidatorAgent',
    'ValidatorResult',
    'AgentOrchestrator',
    'ProcessResult',
]
