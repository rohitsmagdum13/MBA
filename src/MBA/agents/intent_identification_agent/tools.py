"""
Tools for Intent Identification Agent.

This module provides tools for analyzing user queries to identify intents
and extract relevant parameters for member benefit operations.
"""

from strands import tool
from typing import Dict, Any
import json
import boto3
from ...core.settings import settings
from ...core.logging_config import get_logger

logger = get_logger(__name__)


class IntentIdentificationError(Exception):
    """Custom exception for intent identification failures."""
    pass


@tool
async def identify_intent_and_params(query: str) -> Dict[str, Any]:
    """
    Identify intent and extract parameters from user query.
    
    This tool analyzes natural language queries to determine the user's intent
    and extract relevant parameters for member benefit operations.
    
    Args:
        query (str): The user's natural language query to analyze.
                    Examples:
                    - "What's my deductible for member M1001?"
                    - "Check Massage Therapy benefits for John Doe"
                    - "Verify my identity, DOB 1990-05-15"
    
    Returns:
        Dict[str, Any]: A dictionary containing:
            - status (str): "success" if successful, "error" if failed
            - intent (str): Identified intent name if successful
            - params (Dict): Extracted parameters if successful
            - error (str): Error message if failed
            
        Success format:
        {
            "status": "success",
            "intent": "get_deductible_oop",
            "params": {
                "member_id": "M1001",
                "name": null,
                "dob": null,
                "service": null,
                "plan_year": 2025,
                "plan_name": null,
                "group_number": null
            }
        }
        
        Error format:
        {
            "status": "error",
            "error": "Intent identification failed: <error_message>"
        }
    
    Raises:
        IntentIdentificationError: When intent identification fails
        
    Side Effects:
        - Logs debug information about the query analysis
        - May make API calls to Bedrock for intent analysis
    """
    logger.debug(f"Analyzing query for intent: {query}")
    
    try:
        # Create Bedrock client
        session_kwargs = {'region_name': settings.model_region}
        if settings.aws_access_key_id:
            session_kwargs['aws_access_key_id'] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            session_kwargs['aws_secret_access_key'] = settings.aws_secret_access_key
        if settings.aws_profile:
            session_kwargs['profile_name'] = settings.aws_profile
            
        session = boto3.Session(**session_kwargs)
        bedrock_client = session.client('bedrock-runtime')
        
        # Import prompt here to avoid circular imports
        from .prompt import SYSTEM_PROMPT
        
        # Prepare the prompt
        full_prompt = f"{SYSTEM_PROMPT}\n\nUser Query: {query}\n\nAnalyze this query and respond with JSON:"
        
        # Call Bedrock (simplified - in real implementation you'd use proper Bedrock API)
        # For now, we'll use rule-based logic as a fallback
        result = _analyze_query_rule_based(query)
        
        logger.info(f"Intent identified: {result.get('intent')} for query: {query[:50]}...")
        return {
            "status": "success",
            "intent": result["intent"],
            "params": result["params"]
        }
        
    except Exception as e:
        error_msg = f"Intent identification failed: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return {
            "status": "error",
            "error": error_msg
        }


def _analyze_query_rule_based(query: str) -> Dict[str, Any]:
    """
    Rule-based intent analysis as fallback.
    
    Args:
        query (str): User query to analyze
        
    Returns:
        Dict[str, Any]: Intent and parameters
    """
    query_lower = query.lower()
    
    # Initialize default parameters
    params = {
        "member_id": None,
        "name": None,
        "dob": None,
        "service": None,
        "plan_year": 2025,
        "plan_name": None,
        "group_number": None
    }
    
    # Extract member ID patterns
    import re
    member_id_match = re.search(r'member[_\s]*id[=:\s]*([A-Z0-9]+)', query, re.IGNORECASE)
    if member_id_match:
        params["member_id"] = member_id_match.group(1)
    else:
        # Look for M#### pattern
        m_pattern = re.search(r'\bM\d{4}\b', query)
        if m_pattern:
            params["member_id"] = m_pattern.group(0)
    
    # Extract DOB patterns
    dob_match = re.search(r'dob[=:\s]*(\d{4}-\d{2}-\d{2})', query, re.IGNORECASE)
    if dob_match:
        params["dob"] = dob_match.group(1)
    else:
        # Look for date patterns
        date_pattern = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', query)
        if date_pattern:
            params["dob"] = date_pattern.group(1)
    
    # Extract plan_name patterns
    plan_name_match = re.search(r'plan[_\s]*(?:name|id)[=:\s]*([A-Z0-9]+)', query, re.IGNORECASE)
    if plan_name_match:
        params["plan_name"] = plan_name_match.group(1)
    
    # Extract group_number patterns
    group_match = re.search(r'group[_\s]*(?:number|id)[=:\s]*(\d+)', query, re.IGNORECASE)
    if group_match:
        params["group_number"] = group_match.group(1)
    
    # Extract service names
    services = ["massage therapy", "physical therapy", "chiropractic", "acupuncture"]
    for service in services:
        if service in query_lower:
            params["service"] = service.title()
            break
    
    # Extract plan year
    year_match = re.search(r'\b(20\d{2})\b', query)
    if year_match:
        params["plan_year"] = int(year_match.group(1))
    
    # Determine intent based on keywords
    if any(word in query_lower for word in ["verify", "validate", "check identity", "confirm"]):
        intent = "verify_member"
    elif any(word in query_lower for word in ["deductible", "out-of-pocket", "oop", "maximum"]):
        intent = "get_deductible_oop"
    elif any(word in query_lower for word in ["benefit", "remaining", "usage", "accumulator", "balance"]):
        intent = "get_benefit_accumulator"
    else:
        intent = "verify_member"  # Default
    
    return {
        "intent": intent,
        "params": params
    }


async def process_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input data for intent identification.
    
    This function serves as the main entry point for processing intent
    identification requests from various sources (CLI, API, etc.).
    
    Args:
        input_data (Dict[str, Any]): Input data containing:
            - task (str): Should be "identify_intent"
            - query (str): The user query to analyze
    
    Returns:
        Dict[str, Any]: Processing result containing status and result/error
    
    Side Effects:
        - Logs processing information
        - May trigger intent identification analysis
    """
    logger.debug(f"Processing input: {input_data}")
    
    task = input_data.get("task")
    if task == "identify_intent" and "query" in input_data:
        try:
            # Use the strands agent directly
            from .agent import intent_agent
            result = await intent_agent.run({"query": input_data["query"]})
            
            logger.info(f"Intent identification processed successfully")
            return {
                "status": "success",
                "result": result
            }
        except Exception as e:
            error_msg = f"Intent identification processing failed: {str(e)}"
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