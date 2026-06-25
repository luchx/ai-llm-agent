"""
这个文件是 01_BaseAgent.py 的副本，用于被其他文件 import。
请直接阅读 01_BaseAgent.py，那边有完整注释。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel


class AgentResult(BaseModel):
    success: bool
    result: Any
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    token_usage: Optional[Dict[str, int]] = None
    cost: Optional[float] = None


class BaseAgent(ABC):
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.agent_type = self.__class__.__name__

    @abstractmethod
    def process(self, input_json: Dict[str, Any]) -> AgentResult:
        pass

    @abstractmethod
    def get_required_fields(self) -> List[str]:
        pass

    @abstractmethod
    def get_description(self) -> str:
        pass

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        required_fields = self.get_required_fields()
        missing_fields = [f for f in required_fields if f not in input_json]
        if missing_fields:
            raise ValueError(f"缺少必需字段: {missing_fields}")

    def get_agent_info(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "description": self.get_description(),
            "required_fields": self.get_required_fields(),
            "config": self.config,
        }


class UnsupportedAgentError(Exception):
    pass

class ValidationError(Exception):
    pass

class ProcessingError(Exception):
    pass
