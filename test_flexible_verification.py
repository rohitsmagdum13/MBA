"""
Test script for flexible member verification.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from MBA.agents.orchestration_agent import OrchestratorAgent


async def test_flexible_verification():
    """Test orchestrator with flexible verification."""
    
    orchestrator = OrchestratorAgent()
    
    test_queries = [
        "Show all deductible and out-of-pocket information for member_id=M1002 dob=1987-12-14",
        "Give me complete details for member_id=M1002 dob=1987-12-14",
        "What are my benefits for member_id=M1001",
        "Show deductible for plan_name=020213CA",
        "Get benefits for group_number=20213"
    ]
    
    for query in test_queries:
        print(f"\n{'='*80}")
        print(f"Query: {query}")
        print(f"{'='*80}")
        
        try:
            result = await orchestrator.run({"query": query})
            print(f"\n{result.get('summary', 'No summary')}")
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_flexible_verification())
