"""
Tools for Benefit Accumulator Agent.

This module provides tools for retrieving benefit accumulator data
from the MySQL RDS database for member benefit usage tracking.
"""

from strands import tool
from typing import Dict, Any
from sqlalchemy import text
from ...etl.db import connect
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class BenefitAccumulatorError(Exception):
    """Custom exception for benefit accumulator retrieval failures."""
    pass


@tool
async def get_benefit_details(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve benefit accumulator details for a member and service.
    
    This tool queries the benefit_accumulator table to get current benefit
    usage and remaining balances for a specific member and service type.
    
    Args:
        params (Dict[str, Any]): Parameters containing:
            - member_id (str): Member identifier (e.g., "M1001")
            - service (str): Service type (e.g., "Massage Therapy")
            - plan_year (int, optional): Plan year (defaults to 2025)
            
        Example:
        {
            "member_id": "M1001",
            "service": "Massage Therapy",
            "plan_year": 2025
        }
    
    Returns:
        Dict[str, Any]: Benefit accumulator information:
            - status (str): "success" if found, "not_found" if no data
            - member_id (str): Member identifier
            - service (str): Service type
            - allowed_limit (str): Benefit limit description
            - used (int): Amount/sessions used
            - remaining (int): Amount/sessions remaining
            - error (str): Error message if failed
            
        Success format:
        {
            "status": "success",
            "member_id": "M1001",
            "service": "Massage Therapy",
            "allowed_limit": "6 visit calendar year maximum",
            "used": 3,
            "remaining": 3
        }
        
        Not found format:
        {
            "status": "not_found",
            "message": "No benefit accumulator data found for M1001 - Massage Therapy"
        }
        
        Error format:
        {
            "status": "error",
            "error": "Benefit retrieval failed: <error_message>"
        }
    
    Raises:
        BenefitAccumulatorError: When benefit retrieval fails
        
    Side Effects:
        - Logs debug information about the query
        - Executes database query to benefit_accumulator table
    """
    logger.debug(f"Retrieving benefit details with params: {params}")
    
    try:
        member_id = params.get("member_id")
        service = params.get("service")
        plan_year = params.get("plan_year", 2025)
        
        if not member_id or not service:
            return {
                "status": "error",
                "error": "member_id and service are required parameters"
            }
        
        with connect() as conn:
            sql = text("""
                SELECT member_id, service, allowed_limit, used, remaining
                FROM benefit_accumulator 
                WHERE member_id = :member_id 
                AND service = :service
                LIMIT 1
            """)
            
            result = conn.execute(sql, {
                "member_id": member_id,
                "service": service
            }).fetchone()
            
            if result:
                logger.info(f"Benefit details found for {member_id} - {service}")
                return {
                    "status": "success",
                    "member_id": result.member_id,
                    "service": result.service,
                    "allowed_limit": result.allowed_limit,
                    "used": result.used,
                    "remaining": result.remaining
                }
            else:
                logger.warning(f"No benefit data found for {member_id} - {service}")
                return {
                    "status": "not_found",
                    "message": f"No benefit accumulator data found for {member_id} - {service}"
                }
                
    except Exception as e:
        error_msg = f"Benefit retrieval failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg
        }


async def process_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input data for benefit accumulator retrieval.
    
    This function serves as the main entry point for processing benefit
    accumulator requests from various sources (CLI, API, etc.).
    
    Args:
        input_data (Dict[str, Any]): Input data containing:
            - task (str): Should be "get_benefit_details"
            - params (Dict): Parameters for benefit retrieval
            
        Example:
        {
            "task": "get_benefit_details",
            "params": {
                "member_id": "M1001",
                "service": "Massage Therapy",
                "plan_year": 2025
            }
        }
    
    Returns:
        Dict[str, Any]: Processing result containing:
            - status (str): "success", "not_found", or "error"
            - result (Dict): Benefit details if successful
            - error (str): Error message if failed
            
        Success format:
        {
            "status": "success",
            "result": {
                "member_id": "M1001",
                "service": "Massage Therapy",
                "used": 3,
                "remaining": 3
            }
        }
        
        Error format:
        {
            "status": "error",
            "error": "Invalid task or missing parameters"
        }
    
    Side Effects:
        - Logs processing information
        - May trigger database queries
    """
    logger.debug(f"Processing input: {input_data}")
    
    task = input_data.get("task")
    if task == "get_benefit_details" and "params" in input_data:
        try:
            # Use the strands agent directly
            from .agent import accumulator_agent
            result = await accumulator_agent.run({"params": input_data["params"]})
            
            logger.info(f"Benefit accumulator processed successfully")
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            error_msg = f"Benefit accumulator processing failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return {
                "status": "error",
                "error": error_msg
            }
    
    logger.warning(f"Invalid task or missing parameters: {task}")
    return {
        "status": "error",
        "error": "Invalid task or missing parameters"
    }