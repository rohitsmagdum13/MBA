"""
Test cases for Benefit Accumulator Agent.
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

from MBA.agents.benefit_accumulator_agent import BenefitAccumulatorAgent, get_benefit_details

async def test_benefit_accumulator():
    """Test benefit accumulator functionality."""
    
    # Initialize agent
    agent = BenefitAccumulatorAgent()
    
    # Test cases
    test_cases = [
        {
            "member_id": "M1001",
            "service": "Massage Therapy",
            "expected_status": "success"
        },
        {
            "member_id": "M1002", 
            "service": "Smoking Cessation",
            "expected_status": "success"
        },
        {
            "member_id": "M1005",
            "service": "Massage Therapy", 
            "expected_status": "success"
        },
        {
            "member_id": "M9999",
            "service": "Massage Therapy",
            "expected_status": "not_found"
        },
        {
            "member_id": "M1001",
            "service": "Invalid Service",
            "expected_status": "not_found"
        }
    ]
    
    print("🧪 Testing Benefit Accumulator Agent")
    print("=" * 50)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test_case['member_id']} - {test_case['service']}")
        
        try:
            result = await agent.get_benefit_usage(
                test_case['member_id'], 
                test_case['service']
            )
            print(f"Status: {result['status']}")
            print(f"Expected: {test_case['expected_status']}")
            print(f"Match: {'✅' if result['status'] == test_case['expected_status'] else '❌'}")
            
            if result['status'] == 'success':
                print(f"Used: {result['used']}, Remaining: {result['remaining']}")
                print(f"Limit: {result['allowed_limit']}")
            elif result['status'] == 'not_found':
                print(f"Message: {result['message']}")
                
        except Exception as e:
            print(f"Error: {e}")
        
        print("-" * 30)

async def test_all_member_benefits():
    """Test retrieving all benefits for a member."""
    
    print("\n🔄 Testing All Member Benefits")
    print("=" * 35)
    
    agent = BenefitAccumulatorAgent()
    
    test_members = ["M1001", "M1002", "M1003"]
    
    for member_id in test_members:
        print(f"\nMember {member_id}:")
        try:
            results = await agent.get_all_member_benefits(member_id)
            print(f"Found {len(results)} benefit services:")
            
            for result in results:
                print(f"  - {result['service']}: {result['used']} used, {result['remaining']} remaining")
                
        except Exception as e:
            print(f"Error: {e}")

async def test_direct_tool():
    """Test the tool directly."""
    
    print("\n🔧 Testing Direct Tool")
    print("=" * 25)
    
    test_params = {
        'member_id': 'M1001',
        'service': 'Massage Therapy',
        'plan_year': 2025
    }
    
    result = await get_benefit_details(test_params)
    
    print(f"Params: {test_params}")
    print(f"Result: {result}")

def test_agent_info():
    """Test agent information methods."""
    
    print("\n📋 Testing Agent Info")
    print("=" * 20)
    
    agent = BenefitAccumulatorAgent()
    
    info = agent.get_agent_info()
    services = agent.get_supported_services()
    
    print(f"Agent Info: {info}")
    print(f"Supported Services: {services}")

async def test_error_handling():
    """Test error handling."""
    
    print("\n⚠️ Testing Error Handling")
    print("=" * 25)
    
    agent = BenefitAccumulatorAgent()
    
    # Test empty member_id
    try:
        result = await agent.get_benefit_usage("", "Massage Therapy")
    except ValueError as e:
        print(f"Expected ValueError: {e}")
    
    # Test empty service
    try:
        result = await agent.get_benefit_usage("M1001", "")
    except ValueError as e:
        print(f"Expected ValueError: {e}")
    
    # Test valid but non-existent data
    try:
        result = await agent.get_benefit_usage("M1001", "Non-existent Service")
        print(f"Non-existent service result: {result['status']}")
    except Exception as e:
        print(f"Error: {e}")

async def main():
    """Run all tests."""
    await test_benefit_accumulator()
    await test_all_member_benefits()
    await test_direct_tool()
    test_agent_info()
    await test_error_handling()

if __name__ == "__main__":
    asyncio.run(main())