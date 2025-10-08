"""
Deductible and Out-of-Pocket (OOP) Agent for MBA project.

This module provides the main DeductibleOOPAgent class that retrieves
deductible and out-of-pocket expense data from the MySQL RDS database
for member financial tracking and planning.
"""

from strands import Agent
import boto3
from .tools import get_deductible_oop
from .prompt import SYSTEM_PROMPT
from ...core.settings import settings
from ...core.logging_config import get_logger

logger = get_logger(__name__)

# Create Bedrock model client
session_kwargs = {'region_name': settings.model_region}
if settings.aws_access_key_id:
    session_kwargs['aws_access_key_id'] = settings.aws_access_key_id
if settings.aws_secret_access_key:
    session_kwargs['aws_secret_access_key'] = settings.aws_secret_access_key
if settings.aws_profile:
    session_kwargs['profile_name'] = settings.aws_profile

session = boto3.Session(**session_kwargs)
bedrock_model = session.client('bedrock-runtime')

# Create strands agent instance
deductible_oop_agent = Agent(
    name="DeductibleOOPAgent",
    system_prompt=SYSTEM_PROMPT,
    tools=[get_deductible_oop],
    model=bedrock_model
)
