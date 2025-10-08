"""
Tools for Deductible and Out-of-Pocket (OOP) Agent.

This module provides tools for retrieving deductible and OOP data
from the MySQL RDS database using stored procedures.
"""

from strands import tool
from typing import Dict, Any, List, Tuple
from sqlalchemy import text
from ...etl.db import connect
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class DeductibleOOPError(Exception):
    """Custom exception for deductible/OOP retrieval failures."""
    pass


def execute_stored_procedure(procedure_name: str, params: List[Any]) -> Dict[str, Any]:
    """
    Execute a stored procedure and return results.
    
    This function executes MySQL stored procedures with parameters
    and returns the results in a structured format.
    
    Args:
        procedure_name (str): Name of the stored procedure to execute
        params (List[Any]): List of parameters to pass to the procedure
        
    Returns:
        Dict[str, Any]: Execution results containing:
            - status (str): "success" or "error"
            - result (List[Dict]): Query results if successful
            - error (str): Error message if failed
            
    Raises:
        DeductibleOOPError: When stored procedure execution fails
        
    Side Effects:
        - Executes stored procedure in database
        - Logs execution details
    """
    logger.debug(f"Executing stored procedure: {procedure_name} with params: {params}")
    
    try:
        with connect() as conn:
            # Build CALL statement with parameter placeholders
            param_placeholders = ", ".join([":param" + str(i) for i in range(len(params))])
            call_sql = f"CALL {procedure_name}({param_placeholders})"
            
            # Create parameter dictionary
            param_dict = {f"param{i}": param for i, param in enumerate(params)}
            
            logger.debug(f"Executing SQL: {call_sql} with params: {param_dict}")
            
            # Execute the stored procedure
            result = conn.execute(text(call_sql), param_dict)
            
            # Fetch all results
            rows = result.fetchall()
            
            if rows:
                # Convert rows to list of dictionaries
                columns = result.keys()
                result_data = [dict(zip(columns, row)) for row in rows]
                
                logger.info(f"Stored procedure {procedure_name} returned {len(result_data)} rows")
                return {
                    "status": "success",
                    "result": result_data
                }
            else:
                logger.warning(f"Stored procedure {procedure_name} returned no data")
                return {
                    "status": "not_found",
                    "result": []
                }
                
    except Exception as e:
        error_msg = f"Stored procedure execution failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg
        }


@tool
async def get_deductible_oop(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Retrieve deductible and out-of-pocket data using stored procedure.
    
    This tool calls the GetDeductibleOOP stored procedure to retrieve
    comprehensive deductible and OOP information for a member.
    
    Args:
        params (Dict[str, Any]): Parameters containing:
            - member_id (str): Member identifier (e.g., "M1001")
            - plan_year (int): Plan year (e.g., 2025)
            
        Example:
        {
            "member_id": "M1001",
            "plan_year": 2025
        }
    
    Returns:
        Dict[str, Any]: Deductible and OOP information:
            - status (str): "success" if found, "not_found" if no data, "error" if failed
            - member_id (str): Member identifier
            - plan_year (int): Plan year
            - deductible_data (Dict): Structured deductible information
            - error (str): Error message if failed
            
        Success format:
        {
            "status": "success",
            "member_id": "M1001",
            "plan_year": 2025,
            "individual_deductible": {
                "in_network": {"limit": 1500.00, "used": 350.00, "remaining": 1150.00},
                "out_of_network": {"limit": 3000.00, "used": 0.00, "remaining": 3000.00}
            },
            "family_deductible": {
                "in_network": {"limit": 3000.00, "used": 750.00, "remaining": 2250.00},
                "out_of_network": {"limit": 6000.00, "used": 0.00, "remaining": 6000.00}
            },
            "out_of_pocket_maximum": {
                "individual": {
                    "in_network": {"limit": 5000.00, "used": 1200.00, "remaining": 3800.00},
                    "out_of_network": {"limit": 10000.00, "used": 0.00, "remaining": 10000.00}
                },
                "family": {
                    "in_network": {"limit": 10000.00, "used": 2400.00, "remaining": 7600.00},
                    "out_of_network": {"limit": 20000.00, "used": 0.00, "remaining": 20000.00}
                }
            }
        }
        
        Not found format:
        {
            "status": "not_found",
            "message": "No deductible/OOP data found for member M1001 in plan year 2025"
        }
        
        Error format:
        {
            "status": "error",
            "error": "Deductible retrieval failed: <error_message>"
        }
    
    Raises:
        DeductibleOOPError: When deductible retrieval fails
        
    Side Effects:
        - Logs debug information about the query
        - Executes stored procedure GetDeductibleOOP
        - Processes and structures the returned data
    """
    logger.debug(f"Retrieving deductible/OOP data with params: {params}")
    
    try:
        member_id = params.get("member_id")
        plan_year = params.get("plan_year", 2025)
        
        if not member_id:
            return {
                "status": "error",
                "error": "member_id is a required parameter"
            }
        
        if not plan_year:
            return {
                "status": "error", 
                "error": "plan_year is a required parameter"
            }
        
        # Execute the stored procedure
        result = execute_stored_procedure("GetDeductibleOOP", [member_id, plan_year])
        
        if result["status"] == "error":
            return result
        
        if result["status"] == "not_found" or not result["result"]:
            logger.warning(f"No deductible/OOP data found for {member_id} in plan year {plan_year}")
            return {
                "status": "not_found",
                "message": f"No deductible/OOP data found for member {member_id} in plan year {plan_year}"
            }
        
        # Process the stored procedure results
        raw_data = result["result"]
        logger.info(f"Processing {len(raw_data)} deductible/OOP records for {member_id}")
        
        # Structure the data according to the expected format
        structured_data = _structure_deductible_data(raw_data, member_id, plan_year)
        
        logger.info(f"Deductible/OOP data retrieved successfully for {member_id}")
        return structured_data
        
    except Exception as e:
        error_msg = f"Deductible retrieval failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg
        }


def _structure_deductible_data(raw_data: List[Dict[str, Any]], member_id: str, plan_year: int) -> Dict[str, Any]:
    """
    Structure raw deductible data into the expected format.
    
    This helper function processes raw database results and structures
    them into the standardized deductible/OOP format.
    
    Args:
        raw_data (List[Dict[str, Any]]): Raw data from stored procedure
        member_id (str): Member identifier
        plan_year (int): Plan year
        
    Returns:
        Dict[str, Any]: Structured deductible and OOP data
        
    Side Effects:
        - Logs data processing information
        - Calculates remaining amounts
    """
    logger.debug(f"Structuring deductible data for {member_id}")
    
    # Initialize the structured response
    structured = {
        "status": "success",
        "member_id": member_id,
        "plan_year": plan_year,
        "individual_deductible": {
            "in_network": {"limit": 0.0, "used": 0.0, "remaining": 0.0},
            "out_of_network": {"limit": 0.0, "used": 0.0, "remaining": 0.0}
        },
        "family_deductible": {
            "in_network": {"limit": 0.0, "used": 0.0, "remaining": 0.0},
            "out_of_network": {"limit": 0.0, "used": 0.0, "remaining": 0.0}
        },
        "out_of_pocket_maximum": {
            "individual": {
                "in_network": {"limit": 0.0, "used": 0.0, "remaining": 0.0},
                "out_of_network": {"limit": 0.0, "used": 0.0, "remaining": 0.0}
            },
            "family": {
                "in_network": {"limit": 0.0, "used": 0.0, "remaining": 0.0},
                "out_of_network": {"limit": 0.0, "used": 0.0, "remaining": 0.0}
            }
        }
    }
    
    # Process each row from the stored procedure
    for row in raw_data:
        try:
            # Extract values with safe defaults
            deductible_type = str(row.get("deductible_type", "")).lower()
            network_type = str(row.get("network_type", "")).lower().replace("-", "_")
            coverage_level = str(row.get("coverage_level", "")).lower()
            
            limit_amount = float(row.get("limit_amount", 0.0))
            used_amount = float(row.get("used_amount", 0.0))
            remaining_amount = limit_amount - used_amount
            
            # Map to the correct structure
            if deductible_type == "deductible":
                if coverage_level == "individual":
                    if network_type in ["in_network", "out_of_network"]:
                        structured["individual_deductible"][network_type] = {
                            "limit": round(limit_amount, 2),
                            "used": round(used_amount, 2),
                            "remaining": round(remaining_amount, 2)
                        }
                elif coverage_level == "family":
                    if network_type in ["in_network", "out_of_network"]:
                        structured["family_deductible"][network_type] = {
                            "limit": round(limit_amount, 2),
                            "used": round(used_amount, 2),
                            "remaining": round(remaining_amount, 2)
                        }
            elif deductible_type == "out_of_pocket":
                if coverage_level == "individual":
                    if network_type in ["in_network", "out_of_network"]:
                        structured["out_of_pocket_maximum"]["individual"][network_type] = {
                            "limit": round(limit_amount, 2),
                            "used": round(used_amount, 2),
                            "remaining": round(remaining_amount, 2)
                        }
                elif coverage_level == "family":
                    if network_type in ["in_network", "out_of_network"]:
                        structured["out_of_pocket_maximum"]["family"][network_type] = {
                            "limit": round(limit_amount, 2),
                            "used": round(used_amount, 2),
                            "remaining": round(remaining_amount, 2)
                        }
                        
        except Exception as e:
            logger.warning(f"Error processing row {row}: {e}")
            continue
    
    logger.debug(f"Structured deductible data successfully for {member_id}")
    return structured


async def process_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input data for deductible/OOP retrieval.
    
    This function serves as the main entry point for processing deductible
    and OOP requests from various sources (CLI, API, etc.).
    
    Args:
        input_data (Dict[str, Any]): Input data containing:
            - task (str): Should be "get_deductible_oop"
            - params (Dict): Parameters for deductible retrieval
            
        Example:
        {
            "task": "get_deductible_oop",
            "params": {
                "member_id": "M1001",
                "plan_year": 2025
            }
        }
    
    Returns:
        Dict[str, Any]: Processing result containing:
            - status (str): "success", "not_found", or "error"
            - result (Dict): Deductible details if successful
            - error (str): Error message if failed
            
        Success format:
        {
            "status": "success",
            "result": {
                "member_id": "M1001",
                "plan_year": 2025,
                "individual_deductible": {...},
                "family_deductible": {...},
                "out_of_pocket_maximum": {...}
            }
        }
        
        Error format:
        {
            "status": "error",
            "error": "Invalid task or missing parameters"
        }
    
    Side Effects:
        - Logs processing information
        - May trigger stored procedure execution
    """
    logger.debug(f"Processing deductible/OOP input: {input_data}")
    
    task = input_data.get("task")
    if task == "get_deductible_oop" and "params" in input_data:
        try:
            result = await get_deductible_oop(params=input_data["params"])
            
            logger.info("Deductible/OOP processing completed successfully")
            return {
                "status": result.get("status", "success"),
                "result": result
            }
        except Exception as e:
            error_msg = f"Deductible/OOP processing failed: {str(e)}"
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