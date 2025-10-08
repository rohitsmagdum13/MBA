# Orchestrator Query Examples

## CLI Usage

```bash
# Basic deductible query
uv run python -m MBA.cli.cli orchestrate --query "What's my deductible for 2025? member_id=M1001 dob=2005-05-23"

# Benefit accumulator query
uv run python -m MBA.cli.cli orchestrate --query "How much Massage Therapy benefit remaining? member_id=M1001 dob=2005-05-23"

# Member verification
uv run python -m MBA.cli.cli orchestrate --query "Verify my identity member_id=M1002 dob=1987-12-14"
```

## API Usage

```bash
# Start API
uv run python -m MBA.microservices.api

# Query orchestrator
curl -X POST http://localhost:8000/orchestrate \
  -H "Content-Type: application/json" \
  -d '{"query": "What is my deductible for 2025? member_id=M1001 dob=2005-05-23"}'
```

## Streamlit Orchestrator Tab Queries

Based on actual data folder contents, use these queries in the "🤖 Orchestrator" tab:

### Member Verification Queries
- `Verify my identity member_id=M1001 dob=2005-05-23`
- `Check member M1002 with DOB 1987-12-14`
- `Validate member M1003 born 2001-08-30`

### Deductible Queries
- `What's my deductible for 2025? member_id=M1001 dob=2005-05-23`
- `Show deductible remaining for M1002 dob=1987-12-14`
- `How much left on my deductible? member_id=M1003 dob=2001-08-30`

### Benefit Accumulator Queries
- `How much Massage Therapy benefit remaining? member_id=M1001 dob=2005-05-23`
- `Check Smoking Cessation benefits for M1002 dob=1987-12-14`
- `Neurodevelopmental Therapy remaining for M1003 dob=2001-08-30`
- `Show Skilled Nursing Facility benefits M1002 dob=1987-12-14`

### Complete Member Information Queries
- `Show me all my information member_id=M1001 dob=2005-05-23`
- `Give me complete details for member_id=M1002 dob=1987-12-14`
- `What are all my benefits and deductibles? member_id=M1003 dob=2001-08-30`
- `Show everything for member_id=M1004 dob=1977-12-10`
- `Complete member profile for member_id=M1005 dob=1987-01-20`

## Available Test Data

### Members
| Member ID | Name | DOB | Available Benefits |
|-----------|------|-----|-------------------|
| M1001 | Brandi Kim | 2005-05-23 | Massage Therapy (3 remaining), Neurodevelopmental (28 remaining) |
| M1002 | Anthony Brown | 1987-12-14 | All services available, Smoking Cessation (3 remaining) |
| M1003 | Kimberly Ramirez | 2001-08-30 | Multiple services, Neurodevelopmental (10 remaining) |
| M1004 | Jennifer Bolton | 1977-12-10 | Smoking Cessation (6 remaining), Massage Therapy (6 remaining) |
| M1005 | Gabrielle Coleman | 1987-01-20 | Massage Therapy (0 remaining), Neurodevelopmental (0 remaining) |

### Services Available
- Massage Therapy (6 visit maximum)
- Neurodevelopmental Therapy (30 visit maximum)
- Skilled Nursing Facility (100 day maximum)
- Smoking Cessation (8 visit maximum)
- Rehabilitation – Outpatient (30 visit maximum)