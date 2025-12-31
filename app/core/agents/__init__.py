"""
Agent模块

包含所有用于公文处理的Agent
"""
from app.core.agents.base_agent import BaseAgent, AgentResult
from app.core.agents.router_agent import RouterAgent, RouterResult
from app.core.agents.cleaner_agent import CleanerAgent, CleanerResult
from app.core.agents.marker_agent import MarkerAgent, AnalysisResult, DocumentElement
from app.core.agents.validator_agent import ValidatorAgent, ValidatorResult
from app.core.agents.orchestrator import AgentOrchestrator, ProcessResult

__all__ = [
    'BaseAgent',
    'AgentResult',
    'RouterAgent',
    'RouterResult',
    'CleanerAgent',
    'CleanerResult',
    'MarkerAgent',
    'AnalysisResult',
    'DocumentElement',
    'ValidatorAgent',
    'ValidatorResult',
    'AgentOrchestrator',
    'ProcessResult',
]
