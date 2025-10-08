"""
Intent Identification Agent OOP Wrapper for MBA project.

This module provides the IntentIdentificationAgent class that analyzes
user queries to identify intents and extract parameters for member benefit operations.
"""

from typing import Dict, Any, List
from .agent import intent_agent
from ...core.settings import settings
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class IntentIdentificationAgent:
    """
    Intent Identification Agent for analyzing user queries.
    
    This agent uses AWS Bedrock and the strands framework to analyze natural
    language queries and identify the user's intent along with extracting
    relevant parameters for member benefit operations.
    
    The agent supports three main intents:
    1. verify_member: For identity verification
    2. get_deductible_oop: For deductible and out-of-pocket information
    3. get_benefit_accumulator: For benefit usage and remaining balances
    
    Attributes:
        name (str): Agent name for identification and logging
        agent (Agent): Underlying strands Agent instance
        
    Example:
        >>> agent = IntentIdentificationAgent()
        >>> result = await agent.analyze_query("What's my deductible for 2025?")
        >>> print(result["intent"])  # "get_deductible_oop"
    """
    
    def __init__(self, name: str = "IntentIdentificationAgent") -> None:
        """
        Initialize the Intent Identification Agent.
        
        Args:
            name (str, optional): Agent name for logging and identification.
                                Defaults to "IntentIdentificationAgent".
        """
        logger.debug(f"Initializing {name}")
        self.name = name
        self.agent = intent_agent
        logger.info(f"{name} initialized successfully")
    
    async def analyze_query(self, query: str) -> Dict[str, Any]:
        """
        Analyze a user query to identify intent and extract parameters.
        
        Args:
            query (str): The user's natural language query to analyze.
        
        Returns:
            Dict[str, Any]: Analysis result containing intent and parameters
        
        Raises:
            ValueError: If query is empty or invalid
            RuntimeError: If intent identification fails
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        logger.debug(f"{self.name} analyzing query: {query[:100]}...")
        
        try:
            from .tools import identify_intent_and_params
            result = await identify_intent_and_params(query.strip())
            
            if result.get('status') == 'success':
                logger.info(f"Intent identified: {result.get('intent')} for query")
                return {
                    'intent': result['intent'],
                    'params': result['params']
                }
            else:
                raise RuntimeError(result.get('error', 'Intent identification failed'))
            
        except Exception as exc:
            error_msg = f"Query analysis failed: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from exc
    
    async def batch_analyze(self, queries: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple queries in batch.
        
        Args:
            queries (List[str]): List of user queries to analyze
        
        Returns:
            List[Dict[str, Any]]: List of analysis results, one per query
        """
        logger.info(f"Starting batch analysis of {len(queries)} queries")
        
        results = []
        for i, query in enumerate(queries):
            try:
                result = await self.analyze_query(query)
                results.append(result)
                logger.debug(f"Processed query {i+1}/{len(queries)}")
            except Exception as e:
                logger.error(f"Failed to process query {i+1}: {e}")
                results.append({
                    "intent": "verify_member",  # Default fallback
                    "params": {"error": str(e)},
                    "error": True
                })
        
        logger.info(f"Batch analysis completed: {len(results)} results")
        return results
    
    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return ["verify_member", "get_deductible_oop", "get_benefit_accumulator"]
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information and configuration."""
        return {
            "name": self.name,
            "model_provider": "bedrock",
            "model_region": settings.model_region,
            "supported_intents": self.get_supported_intents(),
            "tools_count": 1
        }