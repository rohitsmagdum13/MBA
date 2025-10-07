# Member Verification Agent

The Member Verification Agent validates member identity using MySQL RDS database queries with strands framework integration.

## Features

- **Identity Verification**: Validates member ID, date of birth, and optionally name
- **Database Integration**: Direct MySQL queries using existing ETL infrastructure
- **Multi-Interface Support**: CLI, API, and Streamlit interfaces
- **Error Handling**: Comprehensive error handling and logging
- **Async Support**: Fully asynchronous implementation

## Available Test Data

The system uses the following test members from `MemberData.csv`:

| Member ID | Name | Date of Birth |
|-----------|------|---------------|
| M1001 | Brandi Kim | 2005-05-23 |
| M1002 | Anthony Brown | 1987-12-14 |
| M1003 | Kimberly Ramirez | 2001-08-30 |
| M1004 | Jennifer Bolton | 1977-12-10 |
| M1005 | Gabrielle Coleman | 1987-01-20 |

## Testing Commands

### 1. CLI Commands

```bash
# Test with valid member (Brandi Kim)
uv run python -m MBA.cli.cli verify --member-id M1001 --dob 2005-05-23

# Test with valid member and name
uv run python -m MBA.cli.cli verify --member-id M1001 --dob 2005-05-23 --name "Brandi Kim"

# Test with another valid member (Anthony Brown)
uv run python -m MBA.cli.cli verify --member-id M1002 --dob 1987-12-14

# Test with invalid member
uv run python -m MBA.cli.cli verify --member-id M9999 --dob 1990-01-01

# Test with wrong DOB
uv run python -m MBA.cli.cli verify --member-id M1001 --dob 1990-01-01
```

### 2. API Commands

**Start API server:**
```bash
uv run python -m MBA.microservices.api
```

**Test endpoints:**
```bash
# Test valid member
curl -X POST http://localhost:8000/verify -H "Content-Type: application/json" -d "{\"member_id\": \"M1001\", \"dob\": \"2005-05-23\"}"

# Test with name
curl -X POST http://localhost:8000/verify -H "Content-Type: application/json" -d "{\"member_id\": \"M1001\", \"dob\": \"2005-05-23\", \"name\": \"Brandi Kim\"}"

# Test another valid member
curl -X POST http://localhost:8000/verify -H "Content-Type: application/json" -d "{\"member_id\": \"M1002\", \"dob\": \"1987-12-14\"}"

# Test invalid member
curl -X POST http://localhost:8000/verify -H "Content-Type: application/json" -d "{\"member_id\": \"M9999\", \"dob\": \"1990-01-01\"}"

# Check API health
curl http://localhost:8000/health
```

### 3. Streamlit Interface

```bash
# Start Streamlit app
uv run streamlit run src/MBA/streamlit_app.py
```

**Then in browser:**
1. Go to `http://localhost:8501`
2. Scroll to bottom and expand "🤖 AI Agents"
3. Click "🔍 Member Verification" tab
4. Test these combinations:
   - Member ID: `M1001`, DOB: `2005-05-23`
   - Member ID: `M1002`, DOB: `1987-12-14`
   - Member ID: `M1003`, DOB: `2001-08-30`
   - Member ID: `M9999`, DOB: `1990-01-01` (invalid)

### 4. Direct Tool Test

```bash
# Test the tool directly
uv run python -c "
import asyncio
import sys
sys.path.append('src')

async def test():
    from MBA.agents.member_verification_agent.tools import verify_member
    result = await verify_member({'member_id': 'M1001', 'dob': '2005-05-23'})
    print('Result:', result)

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

- **Valid members**: `{"valid": true, "member_id": "M1001", "name": "Brandi Kim"}`
- **Invalid members**: `{"valid": false, "message": "Authentication failed"}`
- **Errors**: `{"error": "Verification failed: <error message>"}`

## Input Format

```json
{
  "member_id": "M1001",        // Required: Member ID
  "dob": "2005-05-23",         // Required: Date of birth (YYYY-MM-DD)
  "name": "Brandi Kim"         // Optional: Member name
}
```

## Output Format

### Success Response
```json
{
  "valid": true,
  "member_id": "M1001",
  "name": "Brandi Kim"
}
```

### Failure Response
```json
{
  "valid": false,
  "message": "Authentication failed"
}
```

### Error Response
```json
{
  "error": "Verification failed: Database connection error"
}
```

## Configuration

The agent uses configuration from `.env`:

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
CLI/API/Streamlit → verify_member tool → MySQL RDS → memberdata table → Result
```

The agent integrates with:
- Existing MBA database infrastructure
- Strands framework for AI capabilities
- Multi-interface support (CLI, API, Streamlit)
- Centralized settings and logging