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