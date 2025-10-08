"""
Tools for Orchestration Agent.

This module provides tools for orchestrating multiple sub-agents
to handle complex member benefit queries and operations.
"""

from strands import tool
from typing import Dict, Any
from ...core.logging_config import get_logger

logger = get_logger(__name__)


@tool
async def orchestrate_query(params: Dict[str, Any]) -> Dict[str, Any]:
    """Orchestrate query through sub-agents."""
    try:
        query = params.get("query", "")
        
        # Step 1: Identify intent
        from ..intent_identification_agent.wrapper import IntentIdentificationAgent
        intent_agent = IntentIdentificationAgent()
        intent_result = await intent_agent.analyze_query(query)
        
        params_extracted = intent_result.get('params', {})
        
        # Step 2: Verify member with flexible criteria
        verification_params = {}
        if params_extracted.get('member_id'):
            verification_params['member_id'] = params_extracted['member_id']
        if params_extracted.get('dob'):
            verification_params['dob'] = params_extracted['dob']
        if params_extracted.get('plan_name'):
            verification_params['plan_name'] = params_extracted['plan_name']
        if params_extracted.get('group_number'):
            verification_params['group_number'] = params_extracted['group_number']
        
        if not verification_params:
            return {"status": "error", "error": "member_id or dob required (plan_name/group_number not available in current schema)"}
        
        from ..member_verification_agent.wrapper import MemberVerificationAgent
        verification_agent = MemberVerificationAgent()
        from ..member_verification_agent.tools import verify_member
        verification = await verify_member(verification_params)
        
        if not verification.get('valid'):
            return {"status": "error", "error": "Member verification failed"}
        
        member_id = verification.get('member_id')
        member_name = verification.get('name', 'Unknown')
        dob = verification.get('dob', 'Unknown')
        
        # Step 3: Get all information (for "complete" or "everything" queries)
        if any(word in query.lower() for word in ['complete', 'everything', 'all', 'show me']):
            from ..benefit_accumulator_agent.wrapper import BenefitAccumulatorAgent
            from ..deductible_oop_agent.wrapper import DeductibleOOPAgent
            
            accumulator_agent = BenefitAccumulatorAgent()
            deductible_agent = DeductibleOOPAgent()
            
            # Get all benefits
            all_benefits = await accumulator_agent.get_all_member_benefits(member_id)
            
            # Get deductibles
            deductible_info = await deductible_agent.get_deductible_info(member_id, 2025)
            
            # Format output
            output = [f"🧾 Member ID: {member_id} (DOB: {dob})\n"]
            output.append(f"Name: {member_name}\n")
            
            # Benefits section
            if all_benefits:
                output.append("🏥 Benefits")
                for benefit in all_benefits:
                    output.append(f"  {benefit['service']}: {benefit['used']} used, {benefit['remaining']} remaining (Limit: {benefit['allowed_limit']})")
            
            # Deductibles section
            if deductible_info.get('status') == 'success':
                output.append("\n💰 Deductibles / OOP Summary")
                
                ind_ded = deductible_info.get('individual_deductible', {})
                fam_ded = deductible_info.get('family_deductible', {})
                ind_oop = deductible_info.get('out_of_pocket_maximum', {}).get('individual', {})
                fam_oop = deductible_info.get('out_of_pocket_maximum', {}).get('family', {})
                
                output.append(f"  Deductible IND (In-Network): ${ind_ded.get('in_network', {}).get('remaining', 0):.0f} remaining")
                output.append(f"  Deductible FAM (In-Network): ${fam_ded.get('in_network', {}).get('remaining', 0):.0f} remaining")
                output.append(f"  OOP IND (In-Network): ${ind_oop.get('in_network', {}).get('remaining', 0):.0f} remaining")
                output.append(f"  OOP FAM (In-Network): ${fam_oop.get('in_network', {}).get('remaining', 0):.0f} remaining")
            
            # Plan info (from memberdata table via verification)
            output.append("\n🧩 Plan Info")
            output.append(f"  Member verified in system")
            
            return {
                "status": "success",
                "summary": "\n".join(output)
            }
        
        # Handle other intents...
        return {"status": "success", "summary": "Query processed"}
        
    except Exception as e:
        logger.error(f"Orchestration failed: {e}", exc_info=True)
        return {"status": "error", "error": str(e)}



async def process_input(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process input data for orchestration.
    
    Args:
        input_data (Dict[str, Any]): Input data containing task and params
    
    Returns:
        Dict[str, Any]: Processing result
    """
    logger.debug(f"Processing orchestration input: {input_data}")
    
    task = input_data.get("task")
    if task == "orchestrate_query" and "params" in input_data:
        try:
            result = await orchestrate_query(params=input_data["params"])
            logger.info("Orchestration processing completed successfully")
            return {
                "status": result.get("status", "success"),
                "result": result
            }
        except Exception as e:
            error_msg = f"Orchestration processing failed: {str(e)}"
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
