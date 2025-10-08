# Intent Identification Agent

The Intent Identification Agent analyzes user queries to identify intents and extract parameters for member benefit operations using AWS Bedrock and the strands framework.

## Features

- **Intent Classification**: Identifies user intent from natural language queries
- **Parameter Extraction**: Extracts relevant parameters (member_id, dob, service, etc.)
- **Multi-Interface Support**: CLI, API, and Streamlit interfaces
- **Rule-based Fallback**: Fallback logic when AI analysis fails
- **Batch Processing**: Support for analyzing multiple queries
- **Comprehensive Logging**: Detailed logging for debugging and monitoring

## Supported Intents

| Intent | Description | Example Queries |
|--------|-------------|-----------------|
| `verify_member` | Identity verification | "Validate my details", "Check my identity" |
| `get_deductible_oop` | Deductible/out-of-pocket info | "What's my deductible?", "Show OOP maximum" |
| `get_benefit_accumulator` | Benefit usage/remaining | "How much Massage Therapy remaining?" |

## Extracted Parameters

- **member_id**: Member identifier (e.g., "M1001")
- **name**: Member name if mentioned
- **dob**: Date of birth (YYYY-MM-DD format)
- **service**: Specific service (e.g., "Massage Therapy")
- **plan_year**: Plan year (defaults to 2025)
- **plan_name**: Plan identifier (e.g., "020213CA")
- **group_number**: Group identifier (e.g., "20213")

## Testing Commands

### 1. CLI Commands

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
        'Check remaining Massage Therapy benefits for John Doe',
        'Verify my identity, DOB 1990-05-15',
        'How much benefit accumulator remaining for plan 2025?',
        'Show out-of-pocket maximum for group 20213'
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

# Test direct tool
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.intent_identification_agent.tools import identify_intent_and_params
    
    result = await identify_intent_and_params('What is my deductible for member M1001 DOB 1990-05-15?')
    print('Tool result:', result)

asyncio.run(test())
"
```

### 2. API Integration

Add to your API endpoints:

```python
@app.post("/identify-intent")
async def identify_intent(payload: dict):
    """
    Identify intent from user query.
    Payload: {"query": "What's my deductible?"}
    Returns: {"intent": "get_deductible_oop", "params": {...}}
    """
    try:
        from MBA.agents.intent_identification_agent import IntentIdentificationAgent
        agent = IntentIdentificationAgent()
        result = await agent.analyze_query(payload.get("query", ""))
        return result
    except Exception as e:
        return {"error": f"Intent identification failed: {str(e)}"}
```

Test API:
```bash
# Start API server
uv run python -m MBA.microservices.api

# Test intent identification
curl -X POST http://localhost:8000/identify-intent \
  -H "Content-Type: application/json" \
  -d '{"query": "What is my deductible for member M1001?"}'

curl -X POST http://localhost:8000/identify-intent \
  -H "Content-Type: application/json" \
  -d '{"query": "Check remaining Massage Therapy benefits"}'

curl -X POST http://localhost:8000/identify-intent \
  -H "Content-Type: application/json" \
  -d '{"query": "Verify my identity DOB 1990-05-15"}'
```

### 3. Streamlit Integration

Add to your Streamlit app:

```python
# In streamlit_app.py, add to the AI Agents section
with agent_tab3:
    st.write("Analyze user queries to identify intent and extract parameters.")
    
    query = st.text_area(
        "Enter your query:",
        placeholder="What's my deductible for member M1001?",
        height=100
    )
    
    if st.button("Analyze Intent", key="analyze_intent") and query:
        from MBA.agents.intent_identification_agent import IntentIdentificationAgent
        agent = IntentIdentificationAgent()
        
        with st.spinner("Analyzing intent..."):
            result = asyncio.run(agent.analyze_query(query))
        
        col1, col2 = st.columns(2)
        with col1:
            st.success(f"🎯 Intent: **{result['intent']}**")
        with col2:
            st.info(f"📊 Confidence: High")
        
        st.json(result["params"])
```

### 4. Integration Tests

```bash
# Test agent info
uv run python -c "
import sys
sys.path.append('src')
from MBA.agents.intent_identification_agent import IntentIdentificationAgent

agent = IntentIdentificationAgent()
info = agent.get_agent_info()
print('Agent Info:', info)
print('Supported Intents:', agent.get_supported_intents())
"

# Test error handling
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.intent_identification_agent import IntentIdentificationAgent
    agent = IntentIdentificationAgent()
    
    try:
        result = await agent.analyze_query('')  # Empty query
    except ValueError as e:
        print('Expected error:', e)
    
    try:
        result = await agent.analyze_query('Valid query about deductibles')
        print('Success:', result['intent'])
    except Exception as e:
        print('Unexpected error:', e)

asyncio.run(test())
"
```

## Expected Results

### Query: "What's my deductible for member M1001?"
```json
{
  "intent": "get_deductible_oop",
  "params": {
    "member_id": "M1001",
    "name": null,
    "dob": null,
    "service": null,
    "plan_year": 2025,
    "plan_name": null,
    "group_number": null
  }
}
```

### Query: "Check remaining Massage Therapy benefits"
```json
{
  "intent": "get_benefit_accumulator",
  "params": {
    "member_id": null,
    "name": null,
    "dob": null,
    "service": "Massage Therapy",
    "plan_year": 2025,
    "plan_name": null,
    "group_number": null
  }
}
```

### Query: "Verify my identity DOB 1990-05-15"
```json
{
  "intent": "verify_member",
  "params": {
    "member_id": null,
    "name": null,
    "dob": "1990-05-15",
    "service": null,
    "plan_year": 2025,
    "plan_name": null,
    "group_number": null
  }
}
```

## Configuration

Uses settings from `.env`:

- `MODEL_PROVIDER`: Model provider (default: "bedrock")
- `MODEL_NAME`: Bedrock model name
- `MODEL_REGION`: AWS region for Bedrock
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `AWS_PROFILE`: AWS profile name

## Architecture

```
User Query → IntentIdentificationAgent → identify_intent_and_params tool → Rule-based Analysis → Intent + Parameters
```

The agent provides:
- OOP-based design with comprehensive docstrings
- Integration with existing MBA infrastructure
- Fallback mechanisms for reliability
- Multi-interface support (CLI, API, Streamlit)
- Detailed logging and error handling