#!/usr/bin/env python3
"""
Simple test script for Deductible OOP Agent.

This script provides a quick way to test the DeductibleOOPAgent functionality
without running the full test suite.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

from MBA.agents.deductible_oop_agent import DeductibleOOPAgent
from MBA.etl.db import health_check


async def quick_test():
    """Run a quick test of the Deductible OOP Agent."""
    print("🚀 Quick Test: Deductible OOP Agent")
    print("=" * 50)
    
    # Test 1: Database connectivity
    print("\n1. Testing database connectivity...")
    try:
        health = health_check()
        print(f"   Database Status: {health['status']}")
        if health['status'] != 'healthy':
            print(f"   ❌ Database not healthy: {health.get('error', 'Unknown error')}")
            return False
        print("   ✅ Database connection successful")
    except Exception as e:
        print(f"   ❌ Database connection failed: {e}")
        return False
    
    # Test 2: Agent initialization
    print("\n2. Testing agent initialization...")
    try:
        agent = DeductibleOOPAgent()
        agent_info = agent.get_agent_info()
        print(f"   Agent Name: {agent_info['name']}")
        print(f"   Tools Count: {agent_info['tools_count']}")
        print("   ✅ Agent initialized successfully")
    except Exception as e:
        print(f"   ❌ Agent initialization failed: {e}")
        return False
    
    # Test 3: Sample deductible query
    print("\n3. Testing deductible query...")
    try:
        result = await agent.get_deductible_info("M1001", 2025)
        status = result.get('status', 'unknown')
        print(f"   Query Status: {status}")
        
        if status == 'success':
            print("   ✅ Deductible data retrieved successfully")
            # Show sample data structure
            if 'individual_deductible' in result:
                in_network = result['individual_deductible']['in_network']
                print(f"   Sample: Individual In-Network Deductible Remaining: ${in_network.get('remaining', 0):.2f}")
        elif status == 'not_found':
            print("   ⚠️  No deductible data found for test member (this is expected if no test data)")
        else:
            print(f"   ❌ Query failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"   ❌ Deductible query failed: {e}")
        return False
    
    print("\n🎉 Quick test completed successfully!")
    return True


async def interactive_test():
    """Run an interactive test allowing user input."""
    print("\n" + "=" * 50)
    print("🔧 Interactive Test Mode")
    print("=" * 50)
    
    agent = DeductibleOOPAgent()
    
    while True:
        print("\nEnter test parameters (or 'quit' to exit):")
        member_id = input("Member ID (e.g., M1001): ").strip()
        
        if member_id.lower() == 'quit':
            break
            
        if not member_id:
            print("❌ Member ID is required")
            continue
            
        try:
            plan_year = int(input("Plan Year (e.g., 2025): ").strip() or "2025")
        except ValueError:
            print("❌ Invalid plan year, using 2025")
            plan_year = 2025
        
        print(f"\n🔍 Querying deductible info for {member_id} in {plan_year}...")
        
        try:
            result = await agent.get_deductible_info(member_id, plan_year)
            status = result.get('status', 'unknown')
            
            print(f"Status: {status}")
            
            if status == 'success':
                print("\n📊 Deductible Information:")
                print("-" * 30)
                
                # Individual Deductible
                ind_ded = result.get('individual_deductible', {})
                print("Individual Deductible:")
                for network, data in ind_ded.items():
                    print(f"  {network.replace('_', ' ').title()}:")
                    print(f"    Limit: ${data.get('limit', 0):.2f}")
                    print(f"    Used: ${data.get('used', 0):.2f}")
                    print(f"    Remaining: ${data.get('remaining', 0):.2f}")
                
                # Family Deductible
                fam_ded = result.get('family_deductible', {})
                print("\nFamily Deductible:")
                for network, data in fam_ded.items():
                    print(f"  {network.replace('_', ' ').title()}:")
                    print(f"    Limit: ${data.get('limit', 0):.2f}")
                    print(f"    Used: ${data.get('used', 0):.2f}")
                    print(f"    Remaining: ${data.get('remaining', 0):.2f}")
                
            elif status == 'not_found':
                print(f"⚠️  No deductible data found for member {member_id} in {plan_year}")
            else:
                print(f"❌ Query failed: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"❌ Query error: {e}")


def main():
    """Main function to run tests."""
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        asyncio.run(interactive_test())
    else:
        success = asyncio.run(quick_test())
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()