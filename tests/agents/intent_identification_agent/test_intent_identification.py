"""
Test cases for Intent Identification Agent.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from MBA.agents.intent_identification_agent import IntentIdentificationAgent, identify_intent_and_params

async def test_intent_identification():
    """Test intent identification functionality."""
    
    # Initialize agent
    agent = IntentIdentificationAgent()
    
    # Test cases
    test_cases = [
        {
            "query": "What's my deductible for member M1001?",
            "expected_intent": "get_deductible_oop"
        },
        {
            "query": "Check remaining Massage Therapy benefits for John Doe",
            "expected_intent": "get_benefit_accumulator"
        },
        {
            "query": "Verify my identity, DOB 1990-05-15",
            "expected_intent": "verify_member"
        },
        {
            "query": "Show out-of-pocket maximum for 2025",
            "expected_intent": "get_deductible_oop"
        },
        {
            "query": "How much Physical Therapy benefit remaining?",
            "expected_intent": "get_benefit_accumulator"
        }
    ]
    
    print("🧪 Testing Intent Identification Agent")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['query']}")
        
        try:
            result = await agent.analyze_query(test_case['query'])
            print(f"Intent: {result['intent']}")
            print(f"Expected: {test_case['expected_intent']}")
            print(f"Match: {'✅' if result['intent'] == test_case['expected_intent'] else '❌'}")
            print(f"Params: {result['params']}")
        except Exception as e:
            print(f"Error: {e}")
        
        print("-" * 30)

async def test_batch_processing():
    """Test batch processing functionality."""
    
    print("\n🔄 Testing Batch Processing")
    print("=" * 30)
    
    agent = IntentIdentificationAgent()
    
    queries = [
        "What's my deductible?",
        "Check Massage Therapy benefits",
        "Verify member M1001",
        "Show remaining balance for Physical Therapy"
    ]
    
    results = await agent.batch_analyze(queries)
    
    for i, (query, result) in enumerate(zip(queries, results), 1):
        print(f"{i}. Query: {query}")
        print(f"   Intent: {result['intent']}")
        print(f"   Has Error: {'error' in result}")

async def test_direct_tool():
    """Test the tool directly."""
    
    print("\n🔧 Testing Direct Tool")
    print("=" * 25)
    
    test_query = "What is my deductible for member M1001 DOB 1990-05-15?"
    result = await identify_intent_and_params(test_query)
    
    print(f"Query: {test_query}")
    print(f"Result: {result}")

def test_agent_info():
    """Test agent information methods."""
    
    print("\n📋 Testing Agent Info")
    print("=" * 20)
    
    agent = IntentIdentificationAgent()
    
    info = agent.get_agent_info()
    intents = agent.get_supported_intents()
    
    print(f"Agent Info: {info}")
    print(f"Supported Intents: {intents}")

async def main():
    """Run all tests."""
    await test_intent_identification()
    await test_batch_processing()
    await test_direct_tool()
    test_agent_info()

if __name__ == "__main__":
    asyncio.run(main())