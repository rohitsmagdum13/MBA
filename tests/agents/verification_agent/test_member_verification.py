"""
Test cases for Member Verification Agent.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from MBA.agents.member_verification_agent import verification_agent, process

async def test_member_verification():
    """Test member verification functionality."""
    
    # Test valid member
    print("Testing valid member verification...")
    valid_payload = {
        "params": {
            "member_id": "123",
            "dob": "1990-05-15",
            "name": "John Doe"
        }
    }
    
    result = await verification_agent.run(valid_payload)
    print(f"Valid member result: {result}")
    
    # Test invalid member
    print("\nTesting invalid member verification...")
    invalid_payload = {
        "params": {
            "member_id": "999",
            "dob": "1990-01-01",
            "name": "Invalid User"
        }
    }
    
    result = await verification_agent.run(invalid_payload)
    print(f"Invalid member result: {result}")
    
    # Test process function
    print("\nTesting process function...")
    process_payload = {
        "task": "verify_member",
        "params": {
            "member_id": "456",
            "dob": "1985-12-20",
            "name": "Jane Smith"
        }
    }
    
    result = await process(process_payload)
    print(f"Process function result: {result}")

if __name__ == "__main__":
    asyncio.run(test_member_verification())