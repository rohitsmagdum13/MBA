"""
Benefit Accumulator Agent OOP Wrapper for MBA project.

This module provides the BenefitAccumulatorAgent class that retrieves
benefit accumulator data from the MySQL RDS database for member benefit tracking.
"""

from typing import Dict, Any, List
from .agent import accumulator_agent
from ...core.settings import settings
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class BenefitAccumulatorAgent:
    """
    Benefit Accumulator Agent for retrieving member benefit usage data.
    
    This agent uses AWS Bedrock and the strands framework to retrieve benefit
    accumulator information from the MySQL RDS database, showing members their
    current benefit usage and remaining balances for various services.
    
    The agent handles various benefit types including:
    - Massage Therapy
    - Physical Therapy  
    - Neurodevelopmental Therapy
    - Skilled Nursing Facility
    - Smoking Cessation
    - Rehabilitation – Outpatient
    
    Attributes:
        name (str): Agent name for identification and logging
        agent (Agent): Underlying strands Agent instance
        
    Example:
        >>> agent = BenefitAccumulatorAgent()
        >>> result = await agent.get_benefit_usage("M1001", "Massage Therapy")
        >>> print(result["remaining"])  # 3
    """
    
    def __init__(self, name: str = "BenefitAccumulatorAgent") -> None:
        """
        Initialize the Benefit Accumulator Agent.
        
        Args:
            name (str, optional): Agent name for logging and identification.
                                Defaults to "BenefitAccumulatorAgent".
        """
        logger.debug(f"Initializing {name}")
        self.name = name
        self.agent = accumulator_agent
        logger.info(f"{name} initialized successfully")
    
    async def get_benefit_usage(
        self, 
        member_id: str, 
        service: str, 
        plan_year: int = 2025
    ) -> Dict[str, Any]:
        """
        Get benefit usage details for a specific member and service.
        
        Args:
            member_id (str): Member identifier (e.g., "M1001")
            service (str): Service type to query
            plan_year (int, optional): Plan year for the benefits. Defaults to 2025.
        
        Returns:
            Dict[str, Any]: Benefit usage information
        
        Raises:
            ValueError: If member_id or service is empty
            RuntimeError: If benefit retrieval fails
        """
        if not member_id or not member_id.strip():
            raise ValueError("member_id cannot be empty")
        
        if not service or not service.strip():
            raise ValueError("service cannot be empty")
        
        logger.debug(f"{self.name} retrieving benefits for {member_id} - {service}")
        
        try:
            from .tools import get_benefit_details
            result = await get_benefit_details({
                "member_id": member_id.strip(),
                "service": service.strip(),
                "plan_year": plan_year
            })
            
            if result.get('status') == 'success':
                logger.info(f"Benefits retrieved for {member_id} - {service}")
                return result
            elif result.get('status') == 'not_found':
                logger.warning(f"No benefits found for {member_id} - {service}")
                return result
            else:
                raise RuntimeError(result.get('error', 'Benefit retrieval failed'))
            
        except Exception as exc:
            error_msg = f"Benefit retrieval failed: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from exc
    
    async def get_all_member_benefits(self, member_id: str, plan_year: int = 2025) -> List[Dict[str, Any]]:
        """Get all benefit usage details for a specific member."""
        logger.info(f"Retrieving all benefits for member {member_id}")
        
        services = [
            "Massage Therapy", "Physical Therapy", "Neurodevelopmental Therapy",
            "Skilled Nursing Facility", "Smoking Cessation", "Rehabilitation – Outpatient"
        ]
        
        results = []
        for service in services:
            try:
                result = await self.get_benefit_usage(member_id, service, plan_year)
                if result.get('status') == 'success':
                    results.append(result)
            except Exception as e:
                logger.debug(f"No data for {member_id} - {service}: {e}")
                continue
        
        logger.info(f"Retrieved {len(results)} benefit records for {member_id}")
        return results
    
    def get_supported_services(self) -> List[str]:
        """Get list of supported benefit services."""
        return [
            "Massage Therapy", "Physical Therapy", "Neurodevelopmental Therapy", 
            "Skilled Nursing Facility", "Smoking Cessation", "Rehabilitation – Outpatient"
        ]
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information and configuration."""
        return {
            "name": self.name,
            "model_provider": "bedrock",
            "model_region": settings.model_region,
            "supported_services": self.get_supported_services(),
            "tools_count": 1
        }