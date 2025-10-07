MBA S3 Data Ingestion System

📋 Table of Contents

Overview

Architecture

Folder Structure

System Components

Execution Modes

Installation

Configuration

Usage

End-to-End Flow

Function I/O Summary

API Documentation

Database Schema

Monitoring & Logging

Troubleshooting

Security Considerations

License

Contributors

Support



🎯 Overview

The MBA S3 Data Ingestion System is a robust, scalable solution for managing healthcare data uploads from local storage to AWS S3 with subsequent ETL processing into MySQL RDS. The system handles member benefit data and insurance policy documents with intelligent duplicate detection, comprehensive audit trails, and multiple deployment modes.

Key Features

Dual-mode Architecture: Monolithic for simplicity, Microservices for scale

Intelligent Duplicate Detection: MD5 hash-based deduplication

Automatic Scope Detection: Identifies MBA vs Policy data from paths

Comprehensive Audit Trail: Full tracking of all operations

Real-time Monitoring: Streamlit dashboard for visual management

ETL Pipeline: Automatic CSV to MySQL processing via Lambda

Error Recovery: Retry logic with exponential backoff

Bulk Operations: Concurrent uploads with configurable parallelism



🏗 Architecture

High-Level Architecture Diagram

┌─────────────────────────────────────────────────────────────────────────────┐
│                         MBA S3 DATA INGESTION ARCHITECTURE                   │
└─────────────────────────────────────────────────────────────────────────────┘

┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   LOCAL      │      │   STREAMLIT  │      │     CLI      │
│   FILES      │─────▶│      UI      │◀────▶│   INTERFACE  │
└──────────────┘      └──────────────┘      └──────────────┘
                              │                      │
                              ▼                      ▼
                      ┌──────────────────────────────────┐
                      │      CORE INGESTION ENGINE       │
                      │  ┌────────────────────────────┐  │
                      │  │   File Discovery Service   │  │
                      │  ├────────────────────────────┤  │
                      │  │  Duplicate Detection Svc   │  │
                      │  ├────────────────────────────┤  │
                      │  │    S3 Upload Service       │  │
                      │  └────────────────────────────┘  │
                      └──────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
            ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
            │  MONOLITHIC  │ │ MICROSERVICES│ │   LAMBDA     │
            │     MODE     │ │     MODE     │ │   TRIGGER    │
            └──────────────┘ └──────────────┘ └──────────────┘
                    │                 │                 │
                    ▼                 ▼                 ▼
            ┌──────────────────────────────────────────────┐
            │              AWS S3 STORAGE                  │
            │  ┌──────────────┐  ┌──────────────┐        │
            │  │ MBA BUCKET   │  │ POLICY BUCKET│        │
            │  └──────────────┘  └──────────────┘        │
            └──────────────────────────────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────┐
                        │   LAMBDA FUNCTIONS   │
                        │  ┌────────────────┐  │
                        │  │ CSV → RDS ETL  │  │
                        │  └────────────────┘  │
                        └──────────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────┐
                        │    MYSQL RDS         │
                        │  ┌────────────────┐  │
                        │  │ Business Tables│  │
                        │  ├────────────────┤  │
                        │  │  Audit Tables  │  │
                        │  └────────────────┘  │
                        └──────────────────────┘





📁 Folder Structure
mba-ingestion/
├── .env                                  # Environment configuration
├── pyproject.toml                        # Project dependencies & scripts
├── requirements.txt                      # Python dependencies
├── README.md                            # This file
├── LICENSE                              # License information
│
├── logs/                                # Application logs
│   ├── app.log                         # Main application log
│   └── file_cache.json                 # Duplicate detection cache
│
├── data/                                # Data directory
│   ├── mba/                           # MBA scope data
│   │   ├── csv/                       # CSV files for ETL
│   │   │   ├── MemberData.csv
│   │   │   ├── benefit_accumulator.csv
│   │   │   ├── deductibles_oop.csv
│   │   │   └── plan_details.csv
│   │   └── pdf/                       # PDF documents
│   │       └── benefit_coverage.pdf
│   └── policy/                         # Policy scope data
│       ├── csv/                       # Policy CSV files
│       └── pdf/                       # Policy PDFs
│
├── scripts/                             # Utility scripts
│   ├── init.py                        # Database initialization
│   ├── check_duplicates.py           # Standalone duplicate checker
│   └── run_server.sh                  # Server startup script
│
└── src/
    └── MBA/
        ├── __init__.py
        ├── app_launcher.py              # Streamlit launcher
        ├── streamlit_app.py             # Web UI application
        │
        ├── core/                        # Core modules
        │   ├── __init__.py
        │   ├── settings.py             # Configuration management
        │   ├── logging_config.py      # Logging setup
        │   └── exceptions.py           # Custom exceptions
        │
        ├── cli/                         # CLI implementation
        │   ├── __init__.py
        │   └── cli.py                  # Main CLI entry point
        │
        ├── services/                    # Business services
        │   ├── __init__.py
        │   ├── s3_client.py           # S3 operations
        │   ├── file_utils.py          # File discovery & processing
        │   ├── duplicate_detector.py  # Duplicate detection
        │   └── mba_csv_loader.py      # CSV loading orchestration
        │
        ├── etl/                         # ETL components
        │   ├── __init__.py
        │   ├── audit.py               # Audit trail management
        │   ├── csv_schema.py          # Schema inference
        │   ├── db.py                  # Database connectivity
        │   ├── loader.py              # ETL orchestrator
        │   └── transforms.py          # Data transformations
        │
        ├── lambda_handlers/             # Lambda functions
        │   ├── __init__.py
        │   └── csv_ingest_lambda.py   # S3 → RDS ETL handler
        │
        └── microservices/               # Microservices components
            ├── __init__.py
            ├── api.py                  # FastAPI REST service
            ├── producer.py             # Job producer service
            ├── queue.py                # In-memory job queue
            └── worker.py               # Job worker service



🔧 System Components
Core Components

1. Settings Module (core/settings.py)

Purpose: Centralized configuration management using Pydantic
Functionality:

Loads configuration from environment variables and .env file

Validates settings on startup

Provides helper methods for bucket/prefix resolution

Generates database connection URLs

2. Logging Configuration (core/logging_config.py)

Purpose: Standardized logging across all modules
Features:

Dual output: Console and rotating file handlers

Structured format with timestamps, levels, and context

Thread-safe logger management

Prevents duplicate handler configuration

3. Exception Hierarchy (core/exceptions.py)

Purpose: Domain-specific error handling
Exception Types:

MBAIngestionError: Base exception for all errors

ConfigError: Configuration/environment issues

UploadError: S3 upload failures

FileDiscoveryError: Filesystem scanning errors

QueueError: Job queue failures

Service Layer

4. S3 Client (services/s3_client.py)

Key Functions:

build_session(): Creates AWS session with credential resolution

upload_file(): Uploads with retry logic and duplicate detection

check_s3_file_exists(): HEAD-based existence checking

list_s3_files(): Paginated object listing

calculate_file_hash(): MD5/SHA256 computation

5. File Utilities (services/file_utils.py)

Key Functions:

discover_files(): Recursive directory scanning with filters

detect_file_type(): Extension-based type categorization

detect_scope_from_path(): Automatic MBA/Policy detection

build_s3_key(): Structured S3 key generation

6. Duplicate Detector (services/duplicate_detector.py)

Features:

Local file hash computation with caching

S3 duplicate checking via size comparison

Persistent cache in JSON format

Detailed duplicate reports with statistics

ETL Pipeline

7. Database Module (etl/db.py)

Capabilities:

Singleton engine pattern with connection pooling

Automatic database creation if missing

Retry logic with exponential backoff

Bulk insert optimization

Health check endpoints

8. CSV Schema Inference (etl/csv_schema.py)

Process:

Detects CSV delimiter using sniffing

Samples rows for type detection

Infers MySQL data types (DATETIME, BIGINT, VARCHAR, etc.)

Generates CREATE TABLE DDL statements

9. ETL Loader (etl/loader.py)

Pipeline Steps:

Downloads S3 object to memory

Computes MD5 hash for audit

Infers schema from CSV content

Creates table if not exists

Transforms and loads data in batches

Records audit trail

10. Audit System (etl/audit.py)

Tracking:

Operation start/success/failure

Processing duration

Row counts

Error messages

Retry attempts

🚀 Execution Modes

Why Two Modes?
The system supports both Monolithic and Microservices modes to address different deployment scenarios:

Monolithic Mode

Use Case: Small to medium deployments, development, testing
Characteristics:

Single process handles everything

Simple deployment and debugging

Lower latency (no queue overhead)

Limited scalability

How it Works:
User → CLI → File Discovery → Duplicate Check → Direct Upload → S3

Microservices Mode

Use Case: Large-scale production deployments
Characteristics:

Distributed processing across multiple components

Horizontal scalability

Fault isolation

Better resource utilization

Components:

Producer Service (microservices/producer.py)
Role: Job creation and enqueueing
Process:

Discovers files based on criteria

Creates job objects with S3 coordinates

Enqueues jobs for workers
Output: Jobs in queue ready for processing

Queue System (microservices/queue.py)
Role: Job distribution and coordination
Features:

Thread-safe in-memory storage

FIFO processing order

Statistics tracking

Blocking/non-blocking retrieval

Worker Service (microservices/worker.py)
Role: Actual file upload execution
Process:

Retrieves jobs from queue

Performs uploads with retry logic

Updates statistics

Marks jobs complete
Scaling: Multiple workers can run concurrently

API Service (microservices/api.py)
Role: REST interface for job submission
Endpoints:

POST /jobs: Submit new upload job

GET /health: Service health check

GET /stats: Queue statistics

Microservices Flow:
User → Producer → Queue → Workers → S3
      ↓            ↑
    API Service ───────────────┘




📊 End-to-End Flow

Complete System Flow (ASCII)

┌──────────────────────────────────────────────────────────────────────────────────┐
│                            END-TO-END DATA FLOW DIAGRAM                           │
└──────────────────────────────────────────────────────────────────────────────────┘

START
  │
  ▼
┌─────────────────┐
│ User Initiates  │ ──► Method: CLI Command / Streamlit UI / API Call
│    Upload       │
└─────────────────┘
  │
  ▼
┌─────────────────┐
│  Parse Config   │ ──► Load from: .env, CLI args, UI inputs
│  & Validate     │     Validate: AWS creds, buckets, scope
└─────────────────┘
  │
  ▼
┌─────────────────┐
│ Discover Files  │ ──► Scan directories recursively
│                 │     Apply extension filters
│                 │     Detect scope from path
└─────────────────┘
  │
  ▼
┌─────────────────┐
│   Mode Check    │
└─────────────────┘
  │
  ├─[MONOLITHIC]──────────┬─[MICROSERVICES]──────┬─[DUPLICATE_CHECK]
  ▼                       ▼                      ▼
┌──────────────┐    ┌──────────────┐     ┌──────────────┐
│Create        │    │  Producer    │     │  Duplicate   │
│Uploader      │    │  Service     │     │  Scanner     │
└──────────────┘    └──────────────┘     └──────────────┘
  │                       │                      │
  ▼                       ▼                      ▼
┌──────────────┐    ┌──────────────┐     ┌──────────────┐
│Check Local   │    │Create Jobs   │     │ Hash Files   │
│Duplicates    │    │              │     │              │
└──────────────┘    └──────────────┘     └──────────────┘
  │                       │                      │
  ▼                       ▼                      ▼
┌──────────────┐    ┌──────────────┐     ┌──────────────┐
│Check S3      │    │Enqueue Jobs  │     │Compare Hashes│
│Duplicates    │    │              │     │              │
└──────────────┘    └──────────────┘     └──────────────┘
  │                       │                      │
  ▼                       ▼                      ▼
┌──────────────┐    ┌──────────────┐     ┌──────────────┐
│Parallel      │    │Workers       │     │Generate      │
│Upload        │    │Consume       │     │Report        │
└──────────────┘    └──────────────┘     └──────────────┘
  │                       │                      │
  └───────────┬───────────┘                      │
              ▼                                   ▼
      ┌──────────────┐                   ┌──────────────┐
      │  S3 Upload   │                   │Display Report│
      │  with Retry  │                   └──────────────┘
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │ S3 Storage   │
      │ ┌──────────┐ │
      │ │MBA Bucket│ │
      │ ├──────────┤ │
      │ │Policy    │ │
      │ │Bucket    │ │
      │ └──────────┘ │
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │S3 Event      │ ──► Triggers on CSV uploads
      │Notification  │
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │Lambda Function│ ──► csv_ingest_lambda.py
      │Triggered     │
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │Download CSV  │
      │from S3       │
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │Infer Schema  │ ──► Detect types, nullable, lengths
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │Create Table  │ ──► IF NOT EXISTS
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │Transform &   │ ──► Normalize, validate, convert
      │Load Data     │
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │Write Audit   │ ──► Track success/failure
      └──────────────┘
              │
              ▼
      ┌──────────────┐
      │MySQL RDS     │
      │┌────────────┐│
      ││Member Data ││
      │├────────────┤│
      ││Plan Details││
      │├────────────┤│
      ││Deductibles ││
      │├────────────┤│
      ││Accumulator ││
      │├────────────┤│
      ││Audit Trail ││
      │└────────────┘│
      └──────────────┘
              │
              ▼
            END





📥 Installation

Prerequisites

Python 3.9+

AWS Account with S3 and RDS access

MySQL RDS instance (or local MySQL for development)

AWS CLI configured (optional)

Setup Steps

Clone Repository

bashgit clone https://github.com/your-org/mba-ingestion.git
cd mba-ingestion


Create Virtual Environment

bashpython -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate


Install Dependencies

bashpip install -r requirements.txt
# Or using pyproject.toml
pip install -e .


Configure Environment

bashcp .env.example .env
# Edit .env with your AWS and database credentials


Initialize Database

bashpython scripts/init.py

⚙ Configuration

Environment Variables (.env)

ini# AWS Configuration
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=ap-south-1
AWS_PROFILE=default  # Optional, for named profiles

# S3 Buckets
S3_BUCKET_MBA=memberbenefitassistant-bucket
S3_BUCKET_POLICY=policy-bucket
S3_PREFIX_MBA=mba/
S3_PREFIX_POLICY=policy/

# Database Configuration
RDS_HOST=mysql-mba.region.rds.amazonaws.com
RDS_PORT=3306
RDS_DATABASE=mba_mysql
RDS_USERNAME=admin
RDS_PASSWORD=SecurePassword123!
RDS_PARAMS=charset=utf8mb4

# Logging
LOG_LEVEL=INFO
LOG_DIR=logs
LOG_FILE=app.log

🎮 Usage

CLI Commands

Monolithic Mode (Default)

# Basic upload with auto-detection
MBA-ingest --input ./data --auto-detect-scope

# Upload specific scope with filters
MBA-ingest --input ./data --scope mba --include pdf,csv

# Dry run to preview operations
MBA-ingest --input ./data --auto-detect-scope --dry-run

# Force overwrite existing files
MBA-ingest --input ./data --auto-detect-scope --overwrite


Microservices Mode

# Start producer to enqueue jobs
MBA-ingest --mode micro --input ./data --scope mba

# Start workers (in separate terminals)
MBA-worker --concurrency 4

# Start API server
MBA-api


Duplicate Detection

# Check local duplicates only
MBA-ingest --mode check-duplicates --input ./data

# Check against S3 as well
MBA-ingest --mode check-duplicates --input ./data --check-s3


Streamlit UI

# Start web interface
streamlit run src/MBA/streamlit_app.py
# Or using the launcher
MBA-app


API Endpoints

# Submit job via API
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"path": "/data/mba/csv/data.csv", "scope": "mba"}'

# Check health
curl http://localhost:8000/health

# Get statistics
curl http://localhost:8000/stats






































































































































# MBA - S3 Data Ingestion System 🚀

> A production-ready, high-performance data ingestion system for Amazon S3 with intelligent file management and duplicate detection.

## 🎯 Overview

MBA is a flexible data ingestion pipeline that uploads files to Amazon S3 with structured path conventions. It offers both **monolithic** (single process) and **microservices** (distributed queue-based) architectures, making it suitable for everything from quick scripts to enterprise-scale operations.

## ✨ Key Features

- **🏗️ Dual Architecture** - Choose between simple CLI mode or scalable microservices
- **🔍 Intelligent Duplicate Detection** - Local and S3 duplicate checking using MD5 hashing
- **⚡ Concurrent Processing** - Configurable parallel uploads for maximum throughput
- **🎯 Smart Path Convention** - Automatic S3 key generation based on file type and scope
- **🛡️ Production Ready** - Comprehensive error handling, retries, and logging
- **📊 Real-time Monitoring** - API endpoints for health checks and statistics
- **🔧 Flexible Configuration** - Environment-based settings with sensible defaults

## 🏛️ Architecture

### System Overview
```
┌─────────────────────────────────────────────────────────────┐
│                     Input Sources                           │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │   CLI   │  │   API   │  │  Files  │  │  Batch  │       │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
└───────┼────────────┼────────────┼────────────┼─────────────┘
        │            │            │            │
        └────────────┴────────────┴────────────┘
                          │
                    ┌─────▼─────┐
                    │  Producer │ ◄── Discovers files
                    └─────┬─────┘     Creates jobs
                          │
                    ┌─────▼─────┐
                    │ Job Queue │ ◄── Thread-safe queue
                    └─────┬─────┘     Tracks statistics
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐      ┌────▼────┐      ┌────▼────┐
   │ Worker 1│      │ Worker 2│  ... │ Worker N│ ◄── Parallel uploads
   └────┬────┘      └────┬────┘      └────┬────┘
        │                 │                 │
        └─────────────────┴─────────────────┘
                          │
                    ┌─────▼─────┐
                    │ Amazon S3 │
                    └───────────┘
```

### Component Layers
```
┌──────────────────────────────────────────────────────┐
│                    Entry Points                      │
├───────────────┬──────────────┬──────────────────────┤
│    CLI        │     API      │    Streamlit UI      │
│  (cli.py)     │  (api.py)    │ (streamlit_app.py)   │
├───────────────┴──────────────┴──────────────────────┤
│                 Orchestration Layer                  │
├───────────────┬──────────────┬──────────────────────┤
│   Producer    │   Queue      │      Workers         │
│ (producer.py) │  (queue.py)  │    (worker.py)       │
├───────────────┴──────────────┴──────────────────────┤
│                  Services Layer                      │
├───────────────┬──────────────┬──────────────────────┤
│  File Utils   │  S3 Client   │  Duplicate Detector  │
│(file_utils.py)│(s3_client.py)│(duplicate_detector.py)│
├───────────────┴──────────────┴──────────────────────┤
│                    Core Layer                        │
├───────────────┬──────────────┬──────────────────────┤
│   Settings    │   Logging    │    Exceptions        │
│(settings.py)  │(logging.py)  │  (exceptions.py)     │
└───────────────┴──────────────┴──────────────────────┘
```

## 🚀 Quick Start

### Installation
```bash
# Clone the repository
git clone <repo-url> MBA
cd MBA

# Install uv package manager (if needed)
pip install uv

# Install dependencies
uv add boto3 python-dotenv fastapi uvicorn pydantic pydantic-settings
uv pip install -e .
```

### Configuration
Create a `.env` file in the project root:
```env
AWS_PROFILE=your-profile
AWS_REGION=us-west-2
LOG_LEVEL=INFO
WORKER_CONCURRENCY=4

# S3 Buckets
MBA_BUCKET=your-mba-bucket
POLICY_BUCKET=your-policy-bucket

# S3 Prefixes (optional)
MBA_PREFIX=mba/
POLICY_PREFIX=policy/
```

## 📖 Usage Examples

### 1. Simple Upload (Monolithic Mode)
Upload files directly without queue infrastructure:
```bash
# Auto-detect scope from path
MBA-ingest --mode monolith --input ./data/mba/

# Specify scope explicitly
MBA-ingest --mode monolith --input ./documents --scope policy

# Filter by file type
MBA-ingest --mode monolith --input ./data --include pdf,docx
```

### 2. Check for Duplicates
Find duplicate files before uploading:
```bash
# Check local duplicates only
MBA-ingest --mode check-duplicates --input ./data

# Check against S3
MBA-ingest --mode check-duplicates --input ./data --check-s3

# Scope-specific S3 check
MBA-ingest --mode check-duplicates --input ./data --scope mba --check-s3
```

### 3. Microservices Mode
For high-volume processing with distributed components:

**Step 1: Start the API server**
```bash
MBA-api --port 8000
```

**Step 2: Start workers**
```bash
# Start 4 concurrent workers
MBA-worker --concurrency 4
```

**Step 3: Enqueue files**
```bash
# Via Producer CLI
MBA-producer --input ./data --scope mba

# Via API
curl -X POST http://localhost:8000/jobs \
  -H "Content-Type: application/json" \
  -d '{"path": "./data/report.pdf", "scope": "mba"}'
```

**Step 4: Monitor progress**
```bash
# Check queue statistics
curl http://localhost:8000/stats

# Health check
curl http://localhost:8000/health
```

## 🔧 Core Components

### Producer
**Purpose**: Scans directories and creates upload jobs  
**Key Features**:
- Recursive file discovery with filtering
- Automatic scope detection from paths
- Batch job creation for efficient queueing

### Queue
**Purpose**: Thread-safe job management  
**Key Features**:
- In-memory job storage with statistics
- Tracks queued, processed, and failed jobs
- Provides real-time metrics

### Worker
**Purpose**: Processes jobs and uploads to S3  
**Key Features**:
- Configurable concurrency (1-32 threads)
- Automatic retry with exponential backoff
- Duplicate detection before upload

### API
**Purpose**: HTTP interface for remote job submission  
**Key Features**:
- RESTful endpoints for job management
- Health and statistics monitoring
- Validation and error handling

## 📊 Data Flow Examples

### API-Driven Flow
```
Client Request → API validates → Creates Job → Queue → Worker pulls → S3 Upload
     POST           check file      with S3       ↓        job          with retry
    /jobs            exists          key      statistics               & logging
```

### Batch Processing Flow
```
Producer scans → Discovers → Creates Jobs → Queue → Multiple Workers → Parallel S3
    directory      files      with keys       ↓        consume         uploads
                                          statistics     jobs
```

## 🎯 S3 Path Convention

The system automatically generates S3 keys based on file type and scope:

| File Type | Scope | S3 Path Pattern |
|-----------|-------|-----------------|
| PDF | mba | `mba/documents/{filename}.pdf` |
| PDF | policy | `policy/pdfs/{filename}.pdf` |
| Excel | mba | `mba/spreadsheets/{filename}.xlsx` |
| CSV | policy | `policy/data/{filename}.csv` |

## 🛡️ Error Handling

The system implements comprehensive error handling:

- **Retries**: Automatic retry with exponential backoff for transient failures
- **Duplicate Detection**: Prevents redundant uploads using MD5 hashing
- **Validation**: File existence and permission checks before processing
- **Logging**: Detailed logs for debugging and monitoring
- **Graceful Degradation**: Failed jobs don't block the queue

## 📈 Monitoring

### API Endpoints
- `GET /health` - Service health and basic stats
- `GET /stats` - Detailed queue statistics
- `POST /jobs` - Submit new upload job

### Metrics Tracked
- Files queued/processed/failed
- Upload success rate
- Processing throughput
- Worker utilization

## 🔐 Security Features

- **SSE-S3 Encryption**: Server-side encryption for all uploads
- **IAM Role Support**: Uses AWS credentials and profiles
- **Input Validation**: Prevents path traversal attacks
- **Secure Defaults**: Production-ready security settings

## 🚦 Best Practices

1. **For Small Batches** (< 1000 files): Use monolithic mode for simplicity
2. **For Large Batches** (> 1000 files): Use microservices mode with multiple workers
3. **For Continuous Processing**: Run API + workers as services
4. **For One-time Jobs**: Use CLI with `--drain-once` flag
5. **Always Check Duplicates** first to save bandwidth and processing time

## 🔄 Common Workflows

### Daily Data Sync
```bash
# Morning: Check for new files and duplicates
MBA-ingest --mode check-duplicates --input /daily-data --check-s3

# Upload only new files
MBA-ingest --mode monolith --input /daily-data --skip-duplicates
```

### Large Dataset Migration
```bash
# Start infrastructure
MBA-api --port 8000 &
MBA-worker --concurrency 16 &

# Enqueue in batches to avoid memory issues
for dir in /data/*/; do
  MBA-producer --input "$dir" --scope mba
  sleep 60  # Let workers process
done
```

repo-root/
├─ .env
├─ pyproject.toml
├─ requirements.txt
├─ logs/
├─ data/
├─ src/
│  └─ MBA/
│     ├─ core/
│     │  ├─ settings.py
│     │  ├─ logging_config.py
│     │  └─ exceptions.py
│     ├─ services/
│     │  ├─ s3_client.py
│     │  └─ file_utils.py
│     ├─ etl/
│     │  ├─ __init__.py
│     │  ├─ csv_schema.py          # → infer schema & generate CREATE TABLE
│     │  ├─ transforms.py          # → optional row-level transforms
│     │  ├─ db.py                  # → RDS engine + helpers (SQLAlchemy)
│     │  └─ loader.py              # → class: CsvToMySQLLoader
│     └─ lambda_handlers/
│        └─ csv_ingest_lambda.py   # → Lambda entrypoint (S3 trigger)





+--------------------------------------+
| Amazon S3                            |
| memberbenefitassistant-bucket        |
|  └── mba/csv/*.csv                   |
+---------------------+----------------+
                      |
                      | PutObject event
                      v
+--------------------------------------+
| AWS Lambda: mba-csv-rds-ingest       |
| - loads .env settings                |
| - downloads CSV                      |
| - infers schema + CREATE TABLE       |
| - inserts rows (batch)               |
| - (optional) writes audit row        |
+---------------------+----------------+
                      |
                      | MySQL traffic (3306)
                      v
+--------------------------------------+
| Amazon RDS for MySQL (Public)        |
| hma_Mysql DB                         |
| Tables: memberdata,                  |
|         benefit_accumulator,         |
|         deductibles_oop,             |
|         plan_details,                |
|         ingestion_audit (optional)   |
+--------------------------------------+


-- connect to your RDS host as admin
-- host: mysql-hma.cobyueoimrmh.us-east-1.rds.amazonaws.com  port: 3306
-- user: admin  (or your chosen user)
-- then run:
CREATE DATABASE IF NOT EXISTS mba_mysql CHARACTER SET utf8mb4;

-- grant permissions to your ingest user (admin may already have all):
GRANT CREATE, ALTER, INSERT, UPDATE, DELETE, SELECT ON mba_mysql.* TO 'admin'@'%';
FLUSH PRIVILEGES;


















## 🤝 Contributing

Contributions are welcome! The codebase follows these principles:

- **Separation of Concerns**: Each module has a single responsibility
- **Dependency Injection**: Services are loosely coupled
- **Error Handling**: All exceptions are properly caught and logged
- **Type Safety**: Uses Pydantic for validation
- **Testing**: Comprehensive test coverage (see `/tests`)

## 📝 License

[Your License Here]

## 🆘 Support

For issues or questions:
- Check the [Issues](https://github.com/your-repo/issues) page
- Review logs in `./logs/` directory
- Enable debug logging: `LOG_LEVEL=DEBUG`

---
Built with ❤️ for reliable, scalable data ingestion to AWS S3