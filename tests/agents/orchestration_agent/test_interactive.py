"""
Interactive test for orchestration agent without AWS credentials.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent / "src"))


class MockOrchestratorAgent:
    """Mock orchestrator that simulates real behavior."""
    
    def __init__(self):
        self.name = "MockOrchestratorAgent"
        print(f"✅ {self.name} initialized successfully (no AWS required)")
    
    async def run(self, payload):
        """Simulate orchestrator processing."""
        query = payload.get("query", "")
        print(f"🤖 Processing query: {query}")
        
        # Simulate processing time
        await asyncio.sleep(0.5)
        
        # Pattern-based responses
        if "deductible" in query.lower():
            return {
                "summary": "Your deductible for 2025 is $1,500 individual / $3,000 family. You have met $450 so far this year."
            }
        elif "accumulator" in query.lower() or "used" in query.lower():
            return {
                "summary": "Your benefit usage: Medical visits: 8/20 used, Prescription: $1,200/$2,500 used, Dental: 2/4 cleanings used."
            }
        elif "member" in query.lower() and any(x in query for x in ["123", "456", "789"]):
            return {
                "summary": "Member verified successfully. Welcome back! Your plan is active and in good standing."
            }
        elif "benefits" in query.lower() or "coverage" in query.lower():
            return {
                "summary": "Your plan includes: Medical (PPO), Dental (Basic), Vision (Standard). Copays: $25 PCP, $50 Specialist, $15 Generic Rx."
            }
        else:
            return {
                "summary": "I can help with deductibles, benefits, member verification, and benefit accumulators. Please provide more specific information."
            }


async def interactive_test():
    """Interactive test mode."""
    agent = MockOrchestratorAgent()
    
    print("\n" + "="*60)
    print("🎯 INTERACTIVE ORCHESTRATOR TEST")
    print("="*60)
    print("Try these example queries:")
    print("• What's my deductible for 2025? member_id=123")
    print("• How much have I used of my benefits? member_id=456")
    print("• What benefits do I have? member_id=789")
    print("• member_id=123 dob=1990-05-15")
    print("\nType 'quit' to exit")
    print("-"*60)
    
    while True:
        try:
            query = input("\n🔍 Enter your query: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
                print("👋 Goodbye!")
                break
            
            if not query:
                continue
            
            # Run the mock agent
            result = await agent.run({"query": query})
            print(f"\n💬 Response: {result.get('summary', 'No response')}")
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")


async def batch_test():
    """Run predefined test cases."""
    agent = MockOrchestratorAgent()
    
    test_cases = [
        "What's my deductible for 2025? member_id=123 dob=1990-05-15",
        "How much have I used of my medical benefits? member_id=456",
        "What benefits does my plan cover? member_id=789",
        "member_id=123 dob=1990-05-15",
        "Hello, I need help with my insurance"
    ]
    
    print("\n" + "="*60)
    print("🧪 BATCH TEST MODE")
    print("="*60)
    
    for i, query in enumerate(test_cases, 1):
        print(f"\n📝 Test {i}: {query}")
        result = await agent.run({"query": query})
        print(f"✅ Response: {result.get('summary', 'No response')}")
        await asyncio.sleep(0.2)  # Small delay for readability


def main():
    """Main test runner."""
    print("🚀 MBA Orchestration Agent Interactive Test")
    print("No AWS credentials required!")
    
    mode = input("\nChoose test mode:\n1. Interactive\n2. Batch\nEnter choice (1 or 2): ").strip()
    
    if mode == "1":
        asyncio.run(interactive_test())
    elif mode == "2":
        asyncio.run(batch_test())
    else:
        print("Invalid choice. Running batch test...")
        asyncio.run(batch_test())


if __name__ == "__main__":
    main()