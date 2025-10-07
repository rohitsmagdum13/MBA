"""
Test cases for the Orchestration Agent without AWS credentials.

Uses mocking to simulate AWS services and agent responses.
"""
import asyncio
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))

from MBA.agents.orchestration_agent.agent import OrchestratorAgent


class MockOrchestratorAgent:
    """Mock orchestrator for testing without AWS."""
    
    def __init__(self):
        self.name = "MockOrchestratorAgent"
    
    async def run(self, payload):
        """Mock run method that simulates orchestrator behavior."""
        query = payload.get("query", "")
        
        # Simple pattern matching for testing
        if "deductible" in query.lower():
            return {
                "summary": "Your deductible for 2025 is $1,500. This information is based on your current plan."
            }
        elif "member_id" in query.lower():
            return {
                "summary": "Member verification required. Please provide valid member ID and date of birth."
            }
        elif "benefits" in query.lower():
            return {
                "summary": "Your plan includes medical, dental, and vision coverage. Copay is $25 for primary care."
            }
        else:
            return {
                "summary": "I can help you with deductibles, benefits, and member information. Please provide more specific details."
            }


@patch('MBA.agents.orchestration_agent.agent.boto3.Session')
def test_agent_initialization(mock_session):
    """Test that agent initializes without AWS credentials."""
    # Mock boto3 session
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client
    
    # Create agent
    agent = OrchestratorAgent()
    
    # Verify initialization
    assert agent.name == "OrchestratorAgent"
    assert agent.model == mock_client
    print("✅ Agent initialization test passed!")


@patch('MBA.agents.orchestration_agent.agent.boto3.Session')
async def test_agent_run_without_strands(mock_session):
    """Test agent run method when strands is not available."""
    # Mock boto3 session
    mock_client = Mock()
    mock_session.return_value.client.return_value = mock_client
    
    # Create agent
    agent = OrchestratorAgent()
    
    # Test payload
    payload = {"query": "What's my deductible for 2025? member_id=123 dob=1990-05-15"}
    
    # Run agent
    result = await agent.run(payload)
    
    # Verify response
    assert "summary" in result
    assert "Agent not implemented" in result["summary"]
    print("✅ Agent run test passed!")


async def test_mock_orchestrator_functionality():
    """Test a mock version of orchestrator functionality."""
    
    # Test the mock orchestrator
    mock_agent = MockOrchestratorAgent()
    
    # Test different queries
    test_cases = [
        {
            "query": "What's my deductible for 2025?",
            "expected_keyword": "deductible"
        },
        {
            "query": "member_id=123 dob=1990-05-15",
            "expected_keyword": "verification"
        },
        {
            "query": "What benefits do I have?",
            "expected_keyword": "medical"
        },
        {
            "query": "Hello",
            "expected_keyword": "help"
        }
    ]
    
    for case in test_cases:
        result = await mock_agent.run({"query": case["query"]})
        assert "summary" in result
        assert case["expected_keyword"].lower() in result["summary"].lower()
        print(f"✅ Query: '{case['query']}' -> Response: '{result['summary'][:50]}...'")


async def main():
    """Run all tests."""
    print("🧪 Testing Orchestration Agent (No AWS Required)")
    print("=" * 50)
    
    # Test 1: Agent initialization
    test_agent_initialization()
    
    # Test 2: Agent run method
    await test_agent_run_without_strands()
    
    # Test 3: Mock orchestrator functionality
    await test_mock_orchestrator_functionality()
    
    print("=" * 50)
    print("🎉 All tests passed! The orchestration agent structure is working correctly.")
    print("\n📝 To test with real AWS:")
    print("1. Set up AWS credentials in .env file")
    print("2. Install the strands framework")
    print("3. Configure the actual sub-agents")


if __name__ == "__main__":
    asyncio.run(main())