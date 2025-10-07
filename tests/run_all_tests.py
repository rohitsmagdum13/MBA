"""
Test runner for all MBA agent tests.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


async def run_orchestration_tests():
    """Run orchestration agent tests."""
    print("🤖 Running Orchestration Agent Tests")
    print("=" * 40)
    
    # Import and run orchestration tests
    from tests.agents.orchestration_agent.test_orchestration_agent import main as orch_main
    await orch_main()


async def run_intent_tests():
    """Run intent agent tests."""
    print("\n🎯 Running Intent Agent Tests")
    print("=" * 30)
    
    from tests.agents.intent_agent.test_intent_agent import test_intent_agent
    await test_intent_agent()


async def run_verification_tests():
    """Run verification agent tests."""
    print("\n🔐 Running Verification Agent Tests")
    print("=" * 35)
    
    from tests.agents.verification_agent.test_verification_agent import test_verification_agent
    await test_verification_agent()


async def main():
    """Run all tests."""
    print("🚀 MBA Agent Test Suite")
    print("=" * 50)
    
    try:
        await run_orchestration_tests()
        await run_intent_tests()
        await run_verification_tests()
        
        print("\n" + "=" * 50)
        print("🎉 All agent tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Test error: {e}")


if __name__ == "__main__":
    asyncio.run(main())