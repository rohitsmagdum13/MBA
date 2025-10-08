# Benefit Accumulator Agent

The Benefit Accumulator Agent retrieves benefit usage and remaining balances from MySQL RDS database using strands framework integration.

## Features

- **Benefit Usage Tracking**: Shows used vs remaining benefit amounts
- **Multiple Service Types**: Supports various benefit services
- **Database Integration**: Direct MySQL queries using existing ETL infrastructure
- **Multi-Interface Support**: CLI, API, and Streamlit interfaces
- **Error Handling**: Comprehensive error handling and logging
- **Async Support**: Fully asynchronous implementation

## Available Test Data

The system uses the following test data from `benefit_accumulator.csv`:

| Member ID | Service | Allowed Limit | Used | Remaining |
|-----------|---------|---------------|------|-----------|
| M1001 | Massage Therapy | 6 visit calendar year maximum | 3 | 3 |
| M1001 | Neurodevelopmental Therapy | 30 visit calendar year maximum | 2 | 28 |
| M1002 | Massage Therapy | 6 visit calendar year maximum | 0 | 6 |
| M1002 | Smoking Cessation | 8 visit calendar year maximum | 5 | 3 |
| M1003 | Neurodevelopmental Therapy | 30 visit calendar year maximum | 20 | 10 |
| M1005 | Massage Therapy | 6 visit calendar year maximum | 6 | 0 |

## Supported Services

- Massage Therapy
- Physical Therapy
- Neurodevelopmental Therapy
- Skilled Nursing Facility
- Smoking Cessation
- Rehabilitation – Outpatient

## Testing Commands

### 1. CLI Commands

```bash
# Test basic benefit retrieval
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
    
    # Test with no data
    result = await agent.get_benefit_usage('M9999', 'Massage Therapy')
    print('Invalid member:', result)

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

# Test direct tool
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.benefit_accumulator_agent.tools import get_benefit_details
    
    result = await get_benefit_details({
        'member_id': 'M1001',
        'service': 'Massage Therapy',
        'plan_year': 2025
    })
    print('Tool result:', result)

asyncio.run(test())
"
```

### 2. API Integration

Add to your API endpoints:

```python
@app.post("/benefit-accumulator")
async def get_benefit_accumulator(payload: dict):
    """
    Get benefit accumulator data.
    Payload: {"member_id": "M1001", "service": "Massage Therapy", "plan_year": 2025}
    Returns: {"status": "success", "used": 3, "remaining": 3, ...}
    """
    try:
        from MBA.agents.benefit_accumulator_agent import BenefitAccumulatorAgent
        agent = BenefitAccumulatorAgent()
        result = await agent.get_benefit_usage(
            payload.get("member_id", ""),
            payload.get("service", ""),
            payload.get("plan_year", 2025)
        )
        return result
    except Exception as e:
        return {"error": f"Benefit retrieval failed: {str(e)}"}
```

Test API:
```bash
# Start API server
uv run python -m MBA.microservices.api

# Test benefit accumulator
curl -X POST http://localhost:8000/benefit-accumulator \
  -H "Content-Type: application/json" \
  -d '{"member_id": "M1001", "service": "Massage Therapy"}'

curl -X POST http://localhost:8000/benefit-accumulator \
  -H "Content-Type: application/json" \
  -d '{"member_id": "M1002", "service": "Smoking Cessation"}'

curl -X POST http://localhost:8000/benefit-accumulator \
  -H "Content-Type: application/json" \
  -d '{"member_id": "M1005", "service": "Massage Therapy"}'
```

### 3. Streamlit Integration

Add to your Streamlit app:

```python
# In streamlit_app.py, add to the AI Agents section
with agent_tab3:
    st.write("Check benefit usage and remaining balances.")
    
    col1, col2 = st.columns(2)
    with col1:
        member_id = st.text_input("Member ID", placeholder="M1001")
    with col2:
        service = st.selectbox("Service", [
            "Massage Therapy",
            "Physical Therapy", 
            "Neurodevelopmental Therapy",
            "Skilled Nursing Facility",
            "Smoking Cessation",
            "Rehabilitation – Outpatient"
        ])
    
    if st.button("Get Benefit Usage", key="get_benefits") and member_id and service:
        from MBA.agents.benefit_accumulator_agent import BenefitAccumulatorAgent
        agent = BenefitAccumulatorAgent()
        
        with st.spinner("Retrieving benefit data..."):
            result = asyncio.run(agent.get_benefit_usage(member_id, service))
        
        if result.get("status") == "success":
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Used", result["used"])
            with col2:
                st.metric("Remaining", result["remaining"])
            with col3:
                st.info(f"Limit: {result['allowed_limit']}")
        elif result.get("status") == "not_found":
            st.warning("No benefit data found for this member and service")
        else:
            st.error(f"Error: {result.get('error', 'Unknown error')}")
```

### 4. Integration Tests

```bash
# Test agent info
uv run python -c "
import sys
sys.path.append('src')
from MBA.agents.benefit_accumulator_agent import BenefitAccumulatorAgent

agent = BenefitAccumulatorAgent()
info = agent.get_agent_info()
print('Agent Info:', info)
print('Supported Services:', agent.get_supported_services())
"

# Test error handling
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.benefit_accumulator_agent import BenefitAccumulatorAgent
    agent = BenefitAccumulatorAgent()
    
    try:
        result = await agent.get_benefit_usage('', 'Massage Therapy')  # Empty member_id
    except ValueError as e:
        print('Expected error:', e)
    
    try:
        result = await agent.get_benefit_usage('M1001', 'Invalid Service')
        print('Invalid service result:', result['status'])
    except Exception as e:
        print('Error:', e)

asyncio.run(test())
"
```

### 5. Database Health Check

```bash
# Check if database is accessible
uv run python -c "
import sys
sys.path.append('src')
from MBA.etl.db import health_check
print('DB Health:', health_check())
"
```

## Expected Results

### Query: M1001 - Massage Therapy
```json
{
  "status": "success",
  "member_id": "M1001",
  "service": "Massage Therapy",
  "allowed_limit": "6 visit calendar year maximum",
  "used": 3,
  "remaining": 3
}
```

### Query: M1005 - Massage Therapy (Fully Used)
```json
{
  "status": "success",
  "member_id": "M1005",
  "service": "Massage Therapy",
  "allowed_limit": "6 visit calendar year maximum",
  "used": 6,
  "remaining": 0
}
```

### Query: Invalid Member/Service
```json
{
  "status": "not_found",
  "message": "No benefit accumulator data found for M9999 - Massage Therapy"
}
```

## Input Format

```json
{
  "member_id": "M1001",           // Required: Member ID
  "service": "Massage Therapy",   // Required: Service type
  "plan_year": 2025              // Optional: Plan year (defaults to 2025)
}
```

## Output Format

### Success Response
```json
{
  "status": "success",
  "member_id": "M1001",
  "service": "Massage Therapy",
  "allowed_limit": "6 visit calendar year maximum",
  "used": 3,
  "remaining": 3
}
```

### Not Found Response
```json
{
  "status": "not_found",
  "message": "No benefit accumulator data found for M1001 - Invalid Service"
}
```

### Error Response
```json
{
  "status": "error",
  "error": "Benefit retrieval failed: Database connection error"
}
```

## Configuration

Uses settings from `.env`:

- `RDS_HOST`: MySQL RDS endpoint
- `RDS_PORT`: MySQL port (default: 3306)
- `RDS_DATABASE`: Database name
- `RDS_USERNAME`: Database username
- `RDS_PASSWORD`: Database password
- `MODEL_PROVIDER`: Model provider (default: "bedrock")
- `MODEL_NAME`: Bedrock model name
- `MODEL_REGION`: AWS region for Bedrock

## Architecture

```
CLI/API/Streamlit → BenefitAccumulatorAgent → get_benefit_details tool → MySQL RDS → benefit_accumulator table → Result
```

The agent integrates with:
- Existing MBA database infrastructure
- Strands framework for AI capabilities
- Multi-interface support (CLI, API, Streamlit)
- Centralized settings and logging