"""
Test cases for Member Verification Agent.
"""
import asyncio


class MockVerificationAgent:
    """Mock verification agent for testing."""
    
    async def run(self, payload):
        """Mock member verification."""
        params = payload.get("params", {})
        member_id = params.get("member_id")
        dob = params.get("dob")
        
        # Simple mock verification logic
        if member_id in ["123", "456", "789"] and dob:
            return {
                "verified": True,
                "member_id": member_id,
                "name": f"Test Member {member_id}"
            }
        else:
            return {
                "verified": False,
                "error": "Invalid member ID or date of birth"
            }


async def test_verification_agent():
    """Test verification agent functionality."""
    agent = MockVerificationAgent()
    
    test_cases = [
        {"member_id": "123", "dob": "1990-05-15"},
        {"member_id": "456", "dob": "1985-12-20"},
        {"member_id": "999", "dob": "1990-01-01"},
        {"member_id": "123"}  # Missing DOB
    ]
    
    print("🧪 Testing Verification Agent")
    print("=" * 35)
    
    for params in test_cases:
        result = await agent.run({"params": params})
        print(f"Input: {params}")
        print(f"Verified: {result.get('verified', False)}")
        if result.get('verified'):
            print(f"Member: {result.get('name')}")
        else:
            print(f"Error: {result.get('error')}")
        print("-" * 35)


if __name__ == "__main__":
    asyncio.run(test_verification_agent())