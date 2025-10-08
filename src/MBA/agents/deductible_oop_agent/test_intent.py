"""
Test script for Deductible OOP Agent intent identification and functionality.

This script provides comprehensive testing for the DeductibleOOPAgent
including intent identification, parameter validation, and database integration.
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from MBA.agents.deductible_oop_agent import DeductibleOOPAgent
from MBA.agents.deductible_oop_agent.tools import execute_stored_procedure, process_input
from MBA.core.logging_config import get_logger
from MBA.etl.db import health_check

logger = get_logger(__name__)


class DeductibleOOPIntentTester:
    """
    Test class for Deductible OOP Agent intent identification and functionality.
    
    This class provides comprehensive testing capabilities for the DeductibleOOPAgent
    including database connectivity, stored procedure execution, and agent responses.
    """
    
    def __init__(self):
        """Initialize the intent tester."""
        self.agent = DeductibleOOPAgent()
        self.test_results = []
    
    async def test_database_connectivity(self) -> Dict[str, Any]:
        """
        Test database connectivity and health.
        
        Returns:
            Dict[str, Any]: Database health check results
        """
        print("\n" + "="*60)
        print("TESTING DATABASE CONNECTIVITY")
        print("="*60)
        
        try:
            health = health_check()
            print(f"Database Status: {health['status']}")
            print(f"Response Time: {health.get('response_time_ms', 'N/A')}ms")
            print(f"Database: {health.get('database', 'N/A')}")
            print(f"Host: {health.get('host', 'N/A')}")
            
            if health['status'] == 'healthy':
                print("✅ Database connectivity test PASSED")
                return {"test": "database_connectivity", "status": "passed", "details": health}
            else:
                print(f"❌ Database connectivity test FAILED: {health.get('error', 'Unknown error')}")
                return {"test": "database_connectivity", "status": "failed", "details": health}
                
        except Exception as e:
            error_msg = f"Database connectivity test failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {"test": "database_connectivity", "status": "error", "error": error_msg}
    
    async def test_stored_procedure(self) -> Dict[str, Any]:
        """
        Test stored procedure execution directly.
        
        Returns:
            Dict[str, Any]: Stored procedure test results
        """
        print("\n" + "="*60)
        print("TESTING STORED PROCEDURE EXECUTION")
        print("="*60)
        
        try:
            # Test with sample parameters
            test_member_id = "M1001"
            test_plan_year = 2025
            
            print(f"Testing GetDeductibleOOP with member_id: {test_member_id}, plan_year: {test_plan_year}")
            
            result = execute_stored_procedure("GetDeductibleOOP", [test_member_id, test_plan_year])
            
            print(f"Stored Procedure Status: {result['status']}")
            
            if result['status'] == 'success':
                print(f"✅ Stored procedure test PASSED - {len(result['result'])} records returned")
                print("Sample data structure:")
                if result['result']:
                    sample_record = result['result'][0]
                    for key, value in sample_record.items():
                        print(f"  {key}: {value}")
                return {"test": "stored_procedure", "status": "passed", "details": result}
            elif result['status'] == 'not_found':
                print(f"⚠️  Stored procedure test PASSED but no data found for {test_member_id}")
                return {"test": "stored_procedure", "status": "passed_no_data", "details": result}
            else:
                print(f"❌ Stored procedure test FAILED: {result.get('error', 'Unknown error')}")
                return {"test": "stored_procedure", "status": "failed", "details": result}
                
        except Exception as e:
            error_msg = f"Stored procedure test failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {"test": "stored_procedure", "status": "error", "error": error_msg}
    
    async def test_agent_initialization(self) -> Dict[str, Any]:
        """
        Test agent initialization and configuration.
        
        Returns:
            Dict[str, Any]: Agent initialization test results
        """
        print("\n" + "="*60)
        print("TESTING AGENT INITIALIZATION")
        print("="*60)
        
        try:
            agent_info = self.agent.get_agent_info()
            
            print(f"Agent Name: {agent_info['name']}")
            print(f"Model Provider: {agent_info['model_provider']}")
            print(f"Model Region: {agent_info['model_region']}")
            print(f"Tools Count: {agent_info['tools_count']}")
            print(f"Stored Procedure: {agent_info['stored_procedure']}")
            print(f"Supported Network Types: {agent_info['supported_network_types']}")
            print(f"Supported Coverage Levels: {agent_info['supported_coverage_levels']}")
            
            print("✅ Agent initialization test PASSED")
            return {"test": "agent_initialization", "status": "passed", "details": agent_info}
            
        except Exception as e:
            error_msg = f"Agent initialization test failed: {str(e)}"
            print(f"❌ {error_msg}")
            return {"test": "agent_initialization", "status": "error", "error": error_msg}
    
    async def test_intent_identification(self) -> Dict[str, Any]:
        """
        Test various intent identification scenarios.
        
        Returns:
            Dict[str, Any]: Intent identification test results
        """
        print("\n" + "="*60)
        print("TESTING INTENT IDENTIFICATION")
        print("="*60)
        
        test_cases = [
            {
                "name": "Valid deductible request",
                "input": {
                    "task": "get_deductible_oop",
                    "params": {
                        "member_id": "M1001",
                        "plan_year": 2025
                    }
                },
                "expected_status": ["success", "not_found"]
            },
            {
                "name": "Missing member_id",
                "input": {
                    "task": "get_deductible_oop",
                    "params": {
                        "plan_year": 2025
                    }
                },
                "expected_status": ["error"]
            },
            {
                "name": "Invalid task",
                "input": {
                    "task": "invalid_task",
                    "params": {
                        "member_id": "M1001",
                        "plan_year": 2025
                    }
                },
                "expected_status": ["error"]
            },
            {
                "name": "Missing params",
                "input": {
                    "task": "get_deductible_oop"
                },
                "expected_status": ["error"]
            }
        ]
        
        results = []
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            print(f"Input: {test_case['input']}")
            
            try:
                result = await process_input(test_case['input'])
                status = result.get('status', 'unknown')
                
                print(f"Result Status: {status}")
                
                if status in test_case['expected_status']:
                    print(f"✅ Test PASSED - Expected status: {test_case['expected_status']}")
                    results.append({
                        "test_case": test_case['name'],
                        "status": "passed",
                        "result": result
                    })
                else:
                    print(f"❌ Test FAILED - Expected: {test_case['expected_status']}, Got: {status}")
                    results.append({
                        "test_case": test_case['name'],
                        "status": "failed",
                        "expected": test_case['expected_status'],
                        "actual": status,
                        "result": result
                    })
                    
            except Exception as e:
                error_msg = f"Test case failed: {str(e)}"
                print(f"❌ {error_msg}")
                results.append({
                    "test_case": test_case['name'],
                    "status": "error",
                    "error": error_msg
                })
        
        passed_tests = len([r for r in results if r['status'] == 'passed'])
        total_tests = len(results)
        
        print(f"\nIntent Identification Summary: {passed_tests}/{total_tests} tests passed")
        
        return {
            "test": "intent_identification",
            "status": "passed" if passed_tests == total_tests else "partial",
            "passed": passed_tests,
            "total": total_tests,
            "details": results
        }
    
    async def test_agent_methods(self) -> Dict[str, Any]:
        """
        Test specific agent methods with sample data.
        
        Returns:
            Dict[str, Any]: Agent methods test results
        """
        print("\n" + "="*60)
        print("TESTING AGENT METHODS")
        print("="*60)
        
        test_member_id = "M1001"
        test_plan_year = 2025
        
        methods_to_test = [
            {
                "name": "get_deductible_info",
                "method": self.agent.get_deductible_info,
                "args": [test_member_id, test_plan_year]
            },
            {
                "name": "get_individual_deductible",
                "method": self.agent.get_individual_deductible,
                "args": [test_member_id, test_plan_year, "in_network"]
            },
            {
                "name": "get_family_deductible",
                "method": self.agent.get_family_deductible,
                "args": [test_member_id, test_plan_year, "out_of_network"]
            },
            {
                "name": "get_oop_maximum",
                "method": self.agent.get_oop_maximum,
                "args": [test_member_id, test_plan_year, "individual", "in_network"]
            }
        ]
        
        results = []
        
        for method_test in methods_to_test:
            print(f"\nTesting method: {method_test['name']}")
            
            try:
                result = await method_test['method'](*method_test['args'])
                status = result.get('status', 'unknown')
                
                print(f"Method Status: {status}")
                
                if status in ['success', 'not_found']:
                    print(f"✅ Method test PASSED")
                    results.append({
                        "method": method_test['name'],
                        "status": "passed",
                        "result_status": status
                    })
                else:
                    print(f"❌ Method test FAILED: {result.get('error', 'Unknown error')}")
                    results.append({
                        "method": method_test['name'],
                        "status": "failed",
                        "result": result
                    })
                    
            except Exception as e:
                error_msg = f"Method test failed: {str(e)}"
                print(f"❌ {error_msg}")
                results.append({
                    "method": method_test['name'],
                    "status": "error",
                    "error": error_msg
                })
        
        passed_tests = len([r for r in results if r['status'] == 'passed'])
        total_tests = len(results)
        
        print(f"\nAgent Methods Summary: {passed_tests}/{total_tests} methods passed")
        
        return {
            "test": "agent_methods",
            "status": "passed" if passed_tests == total_tests else "partial",
            "passed": passed_tests,
            "total": total_tests,
            "details": results
        }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """
        Run all tests and provide comprehensive results.
        
        Returns:
            Dict[str, Any]: Complete test results summary
        """
        print("🚀 Starting Deductible OOP Agent Comprehensive Testing")
        print("="*80)
        
        # Run all test categories
        db_test = await self.test_database_connectivity()
        sp_test = await self.test_stored_procedure()
        init_test = await self.test_agent_initialization()
        intent_test = await self.test_intent_identification()
        methods_test = await self.test_agent_methods()
        
        all_results = [db_test, sp_test, init_test, intent_test, methods_test]
        
        # Calculate overall summary
        passed_tests = len([r for r in all_results if r['status'] in ['passed', 'passed_no_data']])
        partial_tests = len([r for r in all_results if r['status'] == 'partial'])
        failed_tests = len([r for r in all_results if r['status'] in ['failed', 'error']])
        total_tests = len(all_results)
        
        print("\n" + "="*80)
        print("🏁 COMPREHENSIVE TEST RESULTS SUMMARY")
        print("="*80)
        print(f"✅ Passed: {passed_tests}")
        print(f"⚠️  Partial: {partial_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"📊 Total: {total_tests}")
        
        overall_status = "passed" if failed_tests == 0 else "partial" if passed_tests > 0 else "failed"
        print(f"🎯 Overall Status: {overall_status.upper()}")
        
        return {
            "overall_status": overall_status,
            "summary": {
                "passed": passed_tests,
                "partial": partial_tests,
                "failed": failed_tests,
                "total": total_tests
            },
            "detailed_results": all_results
        }


async def main():
    """Main function to run the intent identification tests."""
    tester = DeductibleOOPIntentTester()
    results = await tester.run_all_tests()
    
    # Exit with appropriate code
    if results["overall_status"] == "passed":
        sys.exit(0)
    elif results["overall_status"] == "partial":
        sys.exit(1)
    else:
        sys.exit(2)


if __name__ == "__main__":
    asyncio.run(main())