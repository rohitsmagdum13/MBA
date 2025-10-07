"""
Tools for Member Verification Agent.
"""

from strands import tool
from typing import Dict, Any
from sqlalchemy import text
from ...etl.db import connect
from ...core.logging_config import get_logger

logger = get_logger(__name__)

@tool
async def verify_member(params: Dict[str, Any]) -> Dict[str, Any]:
    """Verify member identity using database query.

    Args:
        params: Dictionary containing member_id, dob, and optionally name.

    Returns:
        Dictionary with status, validity, and optional message.
    """
    logger.debug(f"Executing verify_member with params: {params}")
    try:
        with connect() as conn:
            sql = text("""
                SELECT member_id, CONCAT(first_name, ' ', last_name) as name FROM memberdata 
                WHERE member_id = :member_id 
                AND dob = :dob
                LIMIT 1
            """)
            
            result = conn.execute(sql, {
                "member_id": params.get("member_id"),
                "dob": params.get("dob")
            }).fetchone()
            
            if result:
                logger.info(f"Member verified successfully: {params.get('member_id')}")
                return {
                    "valid": True, 
                    "member_id": result.member_id,
                    "name": result.name
                }
            else:
                logger.warning(f"Member verification failed: {params.get('member_id')}")
                return {"valid": False, "message": "Authentication failed"}
                
    except Exception as e:
        logger.error(f"Verification failed: {str(e)}", exc_info=True)
        return {"error": f"Verification failed: {str(e)}"}

async def process(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process input data for member verification."""
    logger.debug(f"Processing input: {input_data}")
    task = input_data.get("task")
    if task == "verify_member" and "params" in input_data:
        try:
            from .agent import verification_agent
            result = await verification_agent.run({"params": input_data["params"]})
            logger.info(f"Member verification processed: {result}")
            return {"status": "success", "result": result}
        except Exception as e:
            logger.error(f"Verification processing failed: {str(e)}", exc_info=True)
            return {"error": f"Verification processing failed: {str(e)}"}
    logger.warning(f"Invalid task or missing parameters: {task}")
    return {"error": "Invalid task or missing parameters"}