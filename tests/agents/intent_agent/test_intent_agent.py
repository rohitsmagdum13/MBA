"""
Test cases for Intent Identification Agent.
"""
import asyncio


class MockIntentAgent:
    """Mock intent agent for testing."""
    
    async def run(self, payload):
        """Mock intent identification."""
        query = payload.get("query", "")
        
        if "deductible" in query.lower():
            return {
                "intent": "get_deductible_oop",
                "params": {"member_id": "123", "plan_year": 2025}
            }
        elif "benefits" in query.lower():
            return {
                "intent": "get_benefits",
                "params": {"member_id": "456", "plan_year": 2025}
            }
        elif "accumulator" in query.lower() or "used" in query.lower():
            return {
                "intent": "get_accumulator",
                "params": {"member_id": "789", "service": "medical", "plan_year": 2025}
            }
        else:
            return {
                "intent": "unknown",
                "params": {}
            }


async def test_intent_agent():
    """Test intent agent functionality."""
    agent = MockIntentAgent()
    
    test_cases = [
        "What's my deductible for 2025?",
        "What benefits do I have?",
        "How much have I used of my medical benefits?",
        "Hello world"
    ]
    
    print("🧪 Testing Intent Agent")
    print("=" * 30)
    
    for query in test_cases:
        result = await agent.run({"query": query})
        print(f"Query: {query}")
        print(f"Intent: {result['intent']}")
        print(f"Params: {result['params']}")
        print("-" * 30)


if __name__ == "__main__":
    asyncio.run(test_intent_agent())