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
    """Verify member identity using flexible criteria.

    Args:
        params: Dictionary with member_id, dob, name, plan_name, or group_number.

    Returns:
        Dictionary with status, validity, and optional message.
    """
    logger.debug(f"Executing verify_member with params: {params}")
    try:
        with connect() as conn:
            # Build dynamic WHERE clause
            conditions = []
            sql_params = {}
            
            if params.get("member_id"):
                conditions.append("member_id = :member_id")
                sql_params["member_id"] = params["member_id"]
            
            if params.get("dob"):
                conditions.append("dob = :dob")
                sql_params["dob"] = params["dob"]
            
            # Note: plan_name and group_number not available in current schema
            # if params.get("plan_name"):
            #     conditions.append("plan_name = :plan_name")
            #     sql_params["plan_name"] = params["plan_name"]
            # 
            # if params.get("group_number"):
            #     conditions.append("group_number = :group_number")
            #     sql_params["group_number"] = params["group_number"]
            
            if not conditions:
                return {"valid": False, "message": "At least one identifier required"}
            
            where_clause = " AND " if len(conditions) > 1 else " OR "
            sql = text(f"""
                SELECT member_id, CONCAT(first_name, ' ', last_name) as name, dob 
                FROM memberdata 
                WHERE {where_clause.join(conditions)}
                LIMIT 1
            """)
            
            result = conn.execute(sql, sql_params).fetchone()
            
            if result:
                logger.info(f"Member verified: {result.member_id}")
                return {
                    "valid": True, 
                    "member_id": result.member_id,
                    "name": result.name,
                    "dob": str(result.dob)
                }
            else:
                logger.warning(f"Member verification failed")
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