"""
Orchestrator Agent (OOP wrapper)

This module exposes a thin object-oriented wrapper around the Strands `Agent`
for the Member Benefit Assistant (MBA) Orchestrator. It wires the agent with:
- System prompt (see prompt.py)
- Tools (see tool.py)
- Foundation model (via utils.model_utils.get_model(...))

Logic is unchanged. We merely encapsulate the construction in a class so the
agent can be initialized, configured, and invoked consistently from CLI, API,
Streamlit, or workers.

Usage:
    orchestrator = OrchestratorAgent()
    result = await orchestrator.run({"query": "What's my 2025 deductible? member_id=123, dob=1990-05-15"})
"""

import logging
import boto3
from .prompt import ORCHESTRATOR_PROMPT
from ...core.settings import settings
from .tools import (
    intent_agent_tool,
    verification_agent_tool,
    deductibles_agent_tool,
    accumulator_agent_tool,
    benefits_query_agent_tool,
    summary_agent_tool,
)

from ...core.logging_config import get_logger  # Project-wide logging factory
logger = get_logger(__name__)

class OrchestratorAgent:
    """
    OOP wrapper for the Orchestrator Agent.

    Attributes
    ----------
    name : str
        Logical name for the agent (helpful for logs/metrics).
    model : Any
        Foundation model handle returned by `get_model("bedrock")`.
    agent : strands.Agent
        The underlying Strands Agent instance with prompt and tools.

    Methods
    -------
    run(payload: dict) -> dict
        Execute the orchestrator with the given input payload. The exact payload
        shape is free-form but should contain user query context, e.g.:
        {"query": "<user natural language>", ...}
    """

    def __init__(self, name: str = "OrchestratorAgent") -> None:
        """
        Create the orchestrator.

        Parameters
        ----------
        name : str, optional
            Friendly name for the agent; defaults to "OrchestratorAgent".
        """
        logger.debug("Initializing %s", name)

        # Create Bedrock model client directly from settings
        session_kwargs = {
            'region_name': settings.model_region
        }
        
        # Only add credentials if they exist
        if settings.aws_access_key_id:
            session_kwargs['aws_access_key_id'] = settings.aws_access_key_id
        if settings.aws_secret_access_key:
            session_kwargs['aws_secret_access_key'] = settings.aws_secret_access_key
        if settings.aws_profile:
            session_kwargs['profile_name'] = settings.aws_profile
            
        session = boto3.Session(**session_kwargs)
        bedrock_model = session.client('bedrock-runtime')

        self.name = name
        self.model = bedrock_model
        # Placeholder for agent initialization (strands not available)
        self.agent = None

        logger.info("%s initialized with Bedrock model and tools.", name)

    async def run(self, payload: dict) -> dict:
        """
        Run the orchestrator against a user payload.

        Parameters
        ----------
        payload : dict
            Free-form input from the caller. At minimum, it should contain the
            user's natural-language query under the key "query". Example:
            {
                "query": "What's my deductible for 2025? Member ID 123, DOB 1990-05-15"
            }

        Returns
        -------
        dict
            A JSON-like dictionary. As per your system prompt, the orchestrator
            returns only: {"summary": "<final user-friendly answer>"}.
        """
        logger.debug("%s.run called with payload: %s", self.name, payload)
        try:
            if self.agent is None:
                return {"summary": "Agent not implemented - strands framework not available"}
            result = await self.agent.run(payload)
            logger.info("%s completed successfully.", self.name)
            return result
        except Exception as exc:
            logger.exception("%s failed with error: %s", self.name, exc)
            return {"summary": f"An error occurred while processing your request: {exc}"}
