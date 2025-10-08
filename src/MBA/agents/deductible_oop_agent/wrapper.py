"""
Deductible and Out-of-Pocket (OOP) Agent OOP Wrapper for MBA project.

This module provides the DeductibleOOPAgent class that retrieves
deductible and out-of-pocket expense data from the MySQL RDS database
for member financial tracking and planning.
"""

from typing import Dict, Any, List
from .agent import deductible_oop_agent
from ...core.settings import settings
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class DeductibleOOPAgent:
    """
    Deductible and Out-of-Pocket (OOP) Agent for retrieving member financial data.
    
    This agent uses AWS Bedrock and the strands framework to retrieve deductible
    and out-of-pocket expense information from the MySQL RDS database, helping
    members understand their financial obligations and remaining deductibles.
    
    Attributes:
        name (str): Agent name for identification and logging
        agent (Agent): Underlying strands Agent instance
        
    Example:
        >>> agent = DeductibleOOPAgent()
        >>> result = await agent.get_deductible_info("M1001", 2025)
        >>> print(result["individual_deductible"]["in_network"]["remaining"])  # 1150.00
    """
    
    def __init__(self, name: str = "DeductibleOOPAgent") -> None:
        """Initialize the Deductible and Out-of-Pocket Agent."""
        logger.debug(f"Initializing {name}")
        self.name = name
        self.agent = deductible_oop_agent
        logger.info(f"{name} initialized successfully")
    
    async def get_deductible_info(self, member_id: str, plan_year: int = 2025) -> Dict[str, Any]:
        """
        Get comprehensive deductible and OOP information for a member.
        
        Args:
            member_id (str): Member identifier (e.g., "M1001")
            plan_year (int, optional): Plan year for the deductibles. Defaults to 2025.
        
        Returns:
            Dict[str, Any]: Deductible and OOP information
        
        Raises:
            ValueError: If member_id is empty or plan_year is invalid
            RuntimeError: If deductible retrieval fails
        """
        if not member_id or not member_id.strip():
            raise ValueError("member_id cannot be empty")
        
        if not isinstance(plan_year, int) or plan_year < 2020 or plan_year > 2030:
            raise ValueError("plan_year must be a valid integer between 2020 and 2030")
        
        logger.debug(f"{self.name} retrieving deductible info for {member_id} - {plan_year}")
        
        try:
            from .tools import get_deductible_oop
            result = await get_deductible_oop({
                "member_id": member_id.strip(),
                "plan_year": plan_year
            })
            
            if result.get('status') == 'success':
                logger.info(f"Deductible info retrieved for {member_id} - {plan_year}")
                return result
            elif result.get('status') == 'not_found':
                logger.warning(f"No deductible data found for {member_id} - {plan_year}")
                return result
            else:
                raise RuntimeError(result.get('error', 'Deductible retrieval failed'))
            
        except Exception as exc:
            error_msg = f"Deductible retrieval failed: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from exc
    
    async def get_individual_deductible(
        self, 
        member_id: str, 
        plan_year: int = 2025,
        network_type: str = "in_network"
    ) -> Dict[str, Any]:
        """Get individual deductible information for a specific network type."""
        logger.info(f"Retrieving individual {network_type} deductible for {member_id}")
        
        if network_type not in ["in_network", "out_of_network"]:
            raise ValueError("network_type must be 'in_network' or 'out_of_network'")
        
        full_data = await self.get_deductible_info(member_id, plan_year)
        
        if full_data.get('status') != 'success':
            return full_data
        
        individual_deductible = full_data.get('individual_deductible', {})
        network_data = individual_deductible.get(network_type, {})
        
        return {
            "status": "success",
            "member_id": member_id,
            "plan_year": plan_year,
            "network_type": network_type,
            "deductible": network_data
        }
    
    async def get_family_deductible(
        self, 
        member_id: str, 
        plan_year: int = 2025,
        network_type: str = "in_network"
    ) -> Dict[str, Any]:
        """Get family deductible information for a specific network type."""
        logger.info(f"Retrieving family {network_type} deductible for {member_id}")
        
        if network_type not in ["in_network", "out_of_network"]:
            raise ValueError("network_type must be 'in_network' or 'out_of_network'")
        
        full_data = await self.get_deductible_info(member_id, plan_year)
        
        if full_data.get('status') != 'success':
            return full_data
        
        family_deductible = full_data.get('family_deductible', {})
        network_data = family_deductible.get(network_type, {})
        
        return {
            "status": "success",
            "member_id": member_id,
            "plan_year": plan_year,
            "network_type": network_type,
            "deductible": network_data
        }
    
    async def get_oop_maximum(
        self, 
        member_id: str, 
        plan_year: int = 2025,
        coverage_level: str = "individual",
        network_type: str = "in_network"
    ) -> Dict[str, Any]:
        """Get out-of-pocket maximum information for specific coverage and network."""
        logger.info(f"Retrieving {coverage_level} {network_type} OOP maximum for {member_id}")
        
        if coverage_level not in ["individual", "family"]:
            raise ValueError("coverage_level must be 'individual' or 'family'")
        
        if network_type not in ["in_network", "out_of_network"]:
            raise ValueError("network_type must be 'in_network' or 'out_of_network'")
        
        full_data = await self.get_deductible_info(member_id, plan_year)
        
        if full_data.get('status') != 'success':
            return full_data
        
        oop_maximum = full_data.get('out_of_pocket_maximum', {})
        coverage_data = oop_maximum.get(coverage_level, {})
        network_data = coverage_data.get(network_type, {})
        
        return {
            "status": "success",
            "member_id": member_id,
            "plan_year": plan_year,
            "coverage_level": coverage_level,
            "network_type": network_type,
            "oop_maximum": network_data
        }
    
    def get_supported_network_types(self) -> List[str]:
        """Get list of supported network types."""
        return ["in_network", "out_of_network"]
    
    def get_supported_coverage_levels(self) -> List[str]:
        """Get list of supported coverage levels."""
        return ["individual", "family"]
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information and configuration."""
        return {
            "name": self.name,
            "model_provider": "bedrock",
            "model_region": settings.model_region,
            "supported_network_types": self.get_supported_network_types(),
            "supported_coverage_levels": self.get_supported_coverage_levels(),
            "tools_count": 1,
            "stored_procedure": "GetDeductibleOOP"
        }