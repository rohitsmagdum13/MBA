"""
Simple test for member verification agent.
"""

import asyncio
import sys
sys.path.append('src')

async def test_verification():
    try:
        from MBA.agents.member_verification_agent import verification_agent
        
        print("Testing member verification agent...")
        
        # Test case 1: Valid member
        result1 = await verification_agent.run({
            "params": {
                "member_id": "123",
                "dob": "1990-05-15"
            }
        })
        print(f"Test 1 - Valid member: {result1}")
        
        # Test case 2: Invalid member
        result2 = await verification_agent.run({
            "params": {
                "member_id": "999",
                "dob": "1990-01-01"
            }
        })
        print(f"Test 2 - Invalid member: {result2}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_verification())