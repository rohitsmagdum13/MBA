# MBA Agents Testing Commands

## Testing Commands using UV Package Manager

### 1. Database Health Check
```bash
# Test database connectivity
uv run python -c "
import sys
sys.path.append('src')
from MBA.etl.db import health_check
print('Database Health:', health_check())
"
```

### 2. Intent Identification Agent Tests
```bash
# Test basic intent identification
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.intent_identification_agent import IntentIdentificationAgent
    agent = IntentIdentificationAgent()
    
    queries = [
        'What is my deductible for member M1001?',
        'Check remaining Massage Therapy benefits',
        'Verify my identity DOB 1990-05-15',
        'Show out-of-pocket maximum for 2025'
    ]
    
    for query in queries:
        result = await agent.analyze_query(query)
        print(f'Query: {query}')
        print(f'Intent: {result[\"intent\"]}')
        print(f'Params: {result[\"params\"]}')
        print('-' * 50)

asyncio.run(test())
"

# Test batch processing
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.intent_identification_agent import IntentIdentificationAgent
    agent = IntentIdentificationAgent()
    
    queries = [
        'What is my deductible?',
        'Check Massage Therapy benefits',
        'Verify member M1001'
    ]
    
    results = await agent.batch_analyze(queries)
    for i, result in enumerate(results):
        print(f'Query {i+1}: {result[\"intent\"]} - {result[\"params\"]}')

asyncio.run(test())
"
```

### 3. Member Verification Agent Tests
```bash
# Test with valid member (from test data)
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.member_verification_agent import MemberVerificationAgent
    agent = MemberVerificationAgent()
    
    # Test with valid member
    result = await agent.verify_member('M1001', '2005-05-23')
    print('Valid member test:', result)
    
    # Test with invalid member
    try:
        result = await agent.verify_member('M9999', '1990-01-01')
        print('Invalid member test:', result)
    except Exception as e:
        print('Expected error for invalid member:', e)

asyncio.run(test())
"

# Test direct tool
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.member_verification_agent.tools import verify_member
    result = await verify_member({'member_id': 'M1001', 'dob': '2005-05-23'})
    print('Tool result:', result)

asyncio.run(test())
"
```

### 4. Benefit Accumulator Agent Tests
```bash
# Test benefit usage retrieval
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.benefit_accumulator_agent import BenefitAccumulatorAgent
    agent = BenefitAccumulatorAgent()
    
    # Test with valid member and service
    result = await agent.get_benefit_usage('M1001', 'Massage Therapy')
    print('M1001 Massage Therapy:', result)
    
    # Test with different service
    result = await agent.get_benefit_usage('M1002', 'Smoking Cessation')
    print('M1002 Smoking Cessation:', result)

asyncio.run(test())
"

# Test all benefits for a member
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.benefit_accumulator_agent import BenefitAccumulatorAgent
    agent = BenefitAccumulatorAgent()
    
    results = await agent.get_all_member_benefits('M1001')
    print(f'All benefits for M1001: {len(results)} services')
    for result in results:
        print(f'- {result[\"service\"]}: {result[\"used\"]} used, {result[\"remaining\"]} remaining')

asyncio.run(test())
"
```

### 5. Deductible OOP Agent Tests
```bash
# Test comprehensive deductible info
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.deductible_oop_agent import DeductibleOOPAgent
    agent = DeductibleOOPAgent()
    
    # Test with sample member
    result = await agent.get_deductible_info('M1001', 2025)
    print('Deductible Info Status:', result.get('status'))
    
    if result.get('status') == 'success':
        print('Individual In-Network Deductible:')
        ind_in = result['individual_deductible']['in_network']
        print(f'  Limit: ${ind_in[\"limit\"]:.2f}')
        print(f'  Used: ${ind_in[\"used\"]:.2f}')
        print(f'  Remaining: ${ind_in[\"remaining\"]:.2f}')
    elif result.get('status') == 'not_found':
        print('No deductible data found (expected if no test data)')
    else:
        print('Error:', result.get('error'))

asyncio.run(test())
"

# Test specific deductible methods
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.deductible_oop_agent import DeductibleOOPAgent
    agent = DeductibleOOPAgent()
    
    # Test individual deductible
    result = await agent.get_individual_deductible('M1001', 2025, 'in_network')
    print('Individual Deductible:', result.get('status'))
    
    # Test family deductible
    result = await agent.get_family_deductible('M1001', 2025, 'out_of_network')
    print('Family Deductible:', result.get('status'))
    
    # Test OOP maximum
    result = await agent.get_oop_maximum('M1001', 2025, 'individual', 'in_network')
    print('OOP Maximum:', result.get('status'))

asyncio.run(test())
"

# Test agent info
uv run python -c "
import sys
sys.path.append('src')
from MBA.agents.deductible_oop_agent import DeductibleOOPAgent

agent = DeductibleOOPAgent()
info = agent.get_agent_info()
print('Agent Info:', info)
print('Supported Network Types:', agent.get_supported_network_types())
print('Supported Coverage Levels:', agent.get_supported_coverage_levels())
"
```

### 6. Orchestration Agent Tests
```bash
# Test orchestration with complete flow
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.orchestration_agent import OrchestratorAgent
    orchestrator = OrchestratorAgent()
    
    # Test complete flow with member verification and deductible query
    result = await orchestrator.run({
        'query': 'What is my deductible for member M1001 DOB 2005-05-23?'
    })
    print('Orchestration Result:', result)
    
    # Test benefit accumulator query
    result = await orchestrator.run({
        'query': 'Check my Massage Therapy benefits for member M1001 DOB 2005-05-23'
    })
    print('Benefit Query Result:', result)

asyncio.run(test())
"

# Test orchestration agent info
uv run python -c "
import sys
sys.path.append('src')
from MBA.agents.orchestration_agent import OrchestratorAgent

orchestrator = OrchestratorAgent()
info = orchestrator.get_agent_info()
print('Orchestrator Info:', info)
"
```

### 7. Comprehensive Test Suite
```bash
# Run comprehensive test for deductible OOP agent
uv run python -m MBA.agents.deductible_oop_agent.test_intent

# Test all agents integration
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test_all_agents():
    print('🚀 Testing All MBA Agents')
    print('=' * 50)
    
    # Test 1: Intent Identification
    print('\\n1. Testing Intent Identification...')
    from MBA.agents.intent_identification_agent import IntentIdentificationAgent
    intent_agent = IntentIdentificationAgent()
    result = await intent_agent.analyze_query('What is my deductible for M1001?')
    print(f'   Intent: {result[\"intent\"]}')
    
    # Test 2: Member Verification
    print('\\n2. Testing Member Verification...')
    from MBA.agents.member_verification_agent import MemberVerificationAgent
    verification_agent = MemberVerificationAgent()
    result = await verification_agent.verify_member('M1001', '2005-05-23')
    print(f'   Valid: {result.get(\"valid\", False)}')
    
    # Test 3: Benefit Accumulator
    print('\\n3. Testing Benefit Accumulator...')
    from MBA.agents.benefit_accumulator_agent import BenefitAccumulatorAgent
    accumulator_agent = BenefitAccumulatorAgent()
    result = await accumulator_agent.get_benefit_usage('M1001', 'Massage Therapy')
    print(f'   Status: {result.get(\"status\")}')
    
    # Test 4: Deductible OOP
    print('\\n4. Testing Deductible OOP...')
    from MBA.agents.deductible_oop_agent import DeductibleOOPAgent
    deductible_agent = DeductibleOOPAgent()
    result = await deductible_agent.get_deductible_info('M1001', 2025)
    print(f'   Status: {result.get(\"status\")}')
    
    # Test 5: Orchestration
    print('\\n5. Testing Orchestration...')
    from MBA.agents.orchestration_agent import OrchestratorAgent
    orchestrator = OrchestratorAgent()
    result = await orchestrator.run({'query': 'Verify member M1001 DOB 2005-05-23'})
    print(f'   Summary: {result.get(\"summary\", \"No summary\")}')
    
    print('\\n✅ All agent tests completed!')

asyncio.run(test_all_agents())
"
```

### 8. Error Handling Tests
```bash
# Test error scenarios
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test_errors():
    print('🧪 Testing Error Scenarios')
    print('=' * 40)
    
    from MBA.agents.intent_identification_agent import IntentIdentificationAgent
    from MBA.agents.member_verification_agent import MemberVerificationAgent
    from MBA.agents.deductible_oop_agent import DeductibleOOPAgent
    
    # Test empty query
    try:
        intent_agent = IntentIdentificationAgent()
        await intent_agent.analyze_query('')
    except ValueError as e:
        print('✅ Empty query error handled:', e)
    
    # Test invalid member
    verification_agent = MemberVerificationAgent()
    result = await verification_agent.verify_member('INVALID', '1990-01-01')
    print('✅ Invalid member handled:', result.get('valid', True) == False)
    
    # Test invalid plan year
    try:
        deductible_agent = DeductibleOOPAgent()
        await deductible_agent.get_deductible_info('M1001', 1999)
    except ValueError as e:
        print('✅ Invalid plan year error handled:', e)
    
    print('\\n✅ Error handling tests completed!')

asyncio.run(test_errors())
"
```

## Quick Test Script

For a quick test of the deductible OOP agent, you can also run:

```bash
# Quick test script
uv run python test_deductible_agent.py

# Interactive test mode
uv run python test_deductible_agent.py --interactive
```

## Notes

- All tests use the `uv` package manager as requested
- Tests are designed to work with the existing test data in the database
- Error handling tests verify that agents properly handle invalid inputs
- The comprehensive test suite tests all agents in sequence
- Interactive mode allows manual testing with custom inputs