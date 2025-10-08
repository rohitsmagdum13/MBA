"""
Orchestration Agent OOP Wrapper for MBA project.

This module provides the OrchestratorAgent class that coordinates
multiple sub-agents to handle complex member benefit queries.
"""

from typing import Dict, Any
from .agent import orchestration_agent
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class OrchestratorAgent:
    """
    Orchestrator Agent for coordinating multiple sub-agents.
    
    This agent uses AWS Bedrock and the strands framework to orchestrate
    complex workflows involving intent identification, member verification,
    and business logic execution across multiple specialized agents.
    
    Attributes:
        name (str): Agent name for identification and logging
        agent (Agent): Underlying strands Agent instance
        
    Example:
        >>> orchestrator = OrchestratorAgent()
        >>> result = await orchestrator.run({"query": "What's my deductible? member_id=M1001 dob=2005-05-23"})
        >>> print(result["summary"])
    """
    
    def __init__(self, name: str = "OrchestratorAgent") -> None:
        """
        Initialize the Orchestrator Agent.
        
        Args:
            name (str, optional): Agent name for logging and identification.
                                Defaults to "OrchestratorAgent".
        """
        logger.debug(f"Initializing {name}")
        self.name = name
        self.agent = orchestration_agent
        logger.info(f"{name} initialized successfully")
    
    async def run(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the orchestrator with proper flow: Intent → Verification → Business Logic.
        
        Args:
            payload (Dict[str, Any]): Input containing user query
                                    Example: {"query": "What's my deductible? member_id=M1001 dob=2005-05-23"}
        
        Returns:
            Dict[str, Any]: Final response with user-friendly summary
                          Example: {"summary": "Your 2025 deductible has $1,150 remaining."}
        
        Raises:
            RuntimeError: If orchestration fails
        """
        logger.debug(f"{self.name}.run called with payload: {payload}")
        
        try:
            query = payload.get("query", "")
            if not query:
                return {"summary": "Please provide a query to process."}
            
            # Use the orchestrate_query tool directly
            from .tools import orchestrate_query
            result = await orchestrate_query({"query": query})
            
            if result.get('status') == 'success':
                return {"summary": result.get('summary', 'Query processed successfully.')}
            else:
                error_msg = result.get('error', 'Unknown error occurred')
                logger.error(f"Orchestration failed: {error_msg}")
                return {"summary": f"I encountered an issue: {error_msg}"}
            
        except Exception as exc:
            error_msg = f"Orchestration failed: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            return {"summary": f"An error occurred while processing your request: {str(exc)}"}
    
    def get_agent_info(self) -> Dict[str, Any]:
        """
        Get agent information and configuration.
        
        Returns:
            Dict[str, Any]: Agent information
        """
        return {
            "name": self.name,
            "model_provider": "bedrock",
            "tools_count": 1,
            "purpose": "multi_agent_orchestration",
            "sub_agents": [
                "IntentIdentificationAgent",
                "MemberVerificationAgent", 
                "DeductibleOOPAgent",
                "BenefitAccumulatorAgent"
            ]
        }