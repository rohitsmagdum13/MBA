"""
Member Verification Agent OOP Wrapper for MBA project.

This module provides the MemberVerificationAgent class that wraps
the strands agent for member identity verification operations.
"""

from typing import Dict, Any
from .agent import verification_agent
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class MemberVerificationAgent:
    """
    Member Verification Agent for validating member identity.
    
    This agent uses AWS Bedrock and the strands framework to verify member
    identity using database queries with member ID, date of birth, and name.
    
    Attributes:
        name (str): Agent name for identification and logging
        agent (Agent): Underlying strands Agent instance
        
    Example:
        >>> agent = MemberVerificationAgent()
        >>> result = await agent.verify_member("M1001", "2005-05-23")
        >>> print(result["valid"])  # True
    """
    
    def __init__(self, name: str = "MemberVerificationAgent") -> None:
        """
        Initialize the Member Verification Agent.
        
        Args:
            name (str, optional): Agent name for logging and identification.
                                Defaults to "MemberVerificationAgent".
        """
        logger.debug(f"Initializing {name}")
        self.name = name
        self.agent = verification_agent
        logger.info(f"{name} initialized successfully")
    
    async def verify_member(
        self, 
        member_id: str, 
        dob: str, 
        name: str = None
    ) -> Dict[str, Any]:
        """
        Verify member identity using database lookup.
        
        Args:
            member_id (str): Member identifier (e.g., "M1001")
            dob (str): Date of birth in YYYY-MM-DD format
            name (str, optional): Member name for additional verification
        
        Returns:
            Dict[str, Any]: Verification result containing:
                - valid (bool): True if member is verified
                - member_id (str): Member identifier
                - name (str): Member name if found
                - error (str): Error message if failed
        
        Raises:
            ValueError: If required parameters are missing
            RuntimeError: If verification fails
        """
        if not member_id or not dob:
            raise ValueError("member_id and dob are required")
        
        logger.debug(f"{self.name} verifying member {member_id}")
        
        try:
            from .tools import verify_member
            result = await verify_member({
                "member_id": member_id,
                "dob": dob,
                "name": name
            })
            
            if result.get('valid'):
                logger.info(f"Member {member_id} verified successfully")
            else:
                logger.warning(f"Member {member_id} verification failed")
            
            return result
            
        except Exception as exc:
            error_msg = f"Member verification failed: {str(exc)}"
            logger.error(error_msg, exc_info=True)
            raise RuntimeError(error_msg) from exc
    
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
            "purpose": "member_identity_verification"
        }