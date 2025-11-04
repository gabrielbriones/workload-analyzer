# Workload Analyzer

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-009688.svg)](https://fastapi.tiangolo.com)

An intelligent workload analysis platform that integrates with Intel Simulation Service (ISS) to provide AI-powered insights for workload optimization, compilation improvements, and simulation configuration tuning.

## 🚀 Overview

The Workload Analyzer serves as a bridge between the Intel Simulation Service (ISS) REST API and an AI assistant, enabling users to:

- **Query Workload Data**: Fetch execution jobs and performance metrics from ISS
- **Analyze Results**: Get AI-powered insights on workload performance and optimization opportunities
- **Interactive Chat**: Ask natural language questions about workloads and receive actionable recommendations
- **Performance Optimization**: Receive suggestions for improving code, compilation processes, and simulation configurations

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   User/Client   │───▶│  FastAPI Server  │───▶│ Intel Simulation    │
│                 │    │  (This Project)  │    │ Service (ISS) API   │
└─────────────────┘    └──────────────────┘    └─────────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   AI Assistant   │
                       │  (Auto Bedrock)  │
                       └──────────────────┘
```

## 📋 Features

### Workload Analysis
- **Job Monitoring**: Track execution status across multiple job types (Instance, WorkloadJob, IWPS, ISIM, etc.)
- **Performance Metrics**: Analyze CPU frequency, cache configurations, and execution parameters
- **Platform Support**: Support for multiple target platforms and simulation environments
- **Trace Analysis**: Process different trace types (pinball, littrace, dynamorio, coho_lit)

### AI-Powered Insights
- **Natural Language Interface**: Ask questions about workload performance in plain English
- **Real-time Chat**: WebSocket-based conversational interface with typing indicators
- **Automatic Tool Generation**: Your API endpoints become AI-callable tools automatically
- **Multi-Model Support**: Choose from Claude 4.5, Claude 3.5, OpenAI GPT OSS, Titan, Llama, and more
- **Contextual Analysis**: AI maintains conversation history for deeper workload discussions
- **Smart Recommendations**: Get specific suggestions for improving workload efficiency based on actual data
- **Configuration Tuning**: Receive guidance on optimal simulation parameters with reasoning
- **Error Diagnosis**: AI can analyze failed jobs and suggest remediation steps

### Integration Capabilities
- **RESTful API**: Clean, documented endpoints for all workload operations
- **OpenAPI Auto-Discovery**: AI automatically discovers and can call your API endpoints
- **Real-time WebSocket Chat**: Persistent chat sessions with conversation memory
- **Built-in Web UI**: Professional chat interface - no frontend development needed
- **Security Controls**: Configurable endpoint filtering and authentication
- **Session Management**: Support for concurrent users with session isolation
- **Extensible Architecture**: Easy to add new analysis modules and data sources

## 🤖 AI Assistant Capabilities

The integrated AI assistant powered by **auto-bedrock-chat-fastapi** provides:

### **Intelligent Workload Analysis**
- **"Show me all IWPS jobs running on SPR platforms"** - AI queries `/v1/jobs` and filters by platform and type
- **"What platforms support ISIM workloads?"** - AI calls `/v1/platforms` and analyzes platform capabilities
- **"Get the schema for running Coho jobs on Intel-SPR-8380"** - AI fetches `/v1/jobs/coho/Intel-SPR-8380/schema`
- **"Show me the output files for job a2290337-a3d4-40db-904d-79222997688f"** - AI lists files from `/fs/files/{job_id}/iwps/artifacts/out`
- **"Analyze the performance profile from job a1234567-b2c3-4d5e-6f78-90abcdef1234"** - AI downloads and analyzes simulation results
- **"Compare memory usage between jobs running on different platforms"** - AI retrieves and compares memory profiles

### **Advanced Model Options**
| Model | Use Case | Performance |
|-------|----------|-------------|
| **Claude 4.5 Sonnet** | Complex analysis, deep reasoning | 🚀 **Best for Intel workloads** |
| **Claude 3.5 Haiku** | Quick queries, cost-effective | ⚡ **Fast responses** |
| **OpenAI GPT OSS** | Open-source transparency | 🌐 **Enterprise-friendly** |
| **Llama 3.1 70B** | On-premises options | 🔒 **Data sovereignty** |

### **Automatic API Integration**
The AI assistant automatically discovers and can interact with all your workload analyzer endpoints:

#### **Current Read-Only Operations (v1.0)**
- **Platform Management**: Query platforms (`GET /v1/platforms`), get platform details (`GET /v1/platforms/platform/{PlatformID}`)
- **Job Querying**: List all jobs (`GET /v1/jobs`), get job details (`GET /v1/jobs/job/{JobRequestID}`)
- **Instance Monitoring**: List instances (`GET /v1/instances`), get instance details (`GET /v1/instances/instance/{InstanceID}`)
- **Schema Discovery**: Get IWPS schemas (`GET /v1/jobs/iwps/{Platform}/schema`), ISIM schemas (`GET /v1/jobs/isim/{Platform}/schema`), Coho schemas (`GET /v1/jobs/coho/{Platform}/schema`)
- **File Access**: List job output files (`GET /fs/files/{job_id}/iwps/artifacts/out`), download simulation results and logs
- **Performance Analysis**: Fetch metrics, generate reports, compare configurations
- **Platform Intelligence**: Compare platform capabilities, recommend optimal platforms for workloads

#### **Future Roadmap (Read/Write Operations)**
- **Job Management**: Create, update, and delete simulation jobs
- **Instance Control**: Terminate instances, update metrics settings
- **Platform Administration**: Create and manage platforms (admin functions)

## 📊 Supported Job Types

The system supports analysis for various Intel simulation job types:

| Job Type | Description | Use Case |
|----------|-------------|----------|
| `Instance` | Base simulation instance | General workload execution |
| `WorkloadJob` | Standard workload execution | Performance analysis |
| `WorkloadJobROI` | Region of Interest workloads | Focused performance studies |
| `IWPS` | Intel Workload Performance Simulator | Detailed performance modeling |
| `ISIM` | Intel Simulator | Architecture exploration |
| `NovaIWPS` | Nova-based IWPS execution | Advanced performance analysis |
| `BiosValidation` | BIOS validation runs | Platform validation |

## 🛠️ Data Schema

The project uses a comprehensive JSON schema (`schema_jobs.json`) that defines:

- **Job Metadata**: Request IDs, status, descriptions, and execution details
- **Workload Information**: Names, platforms, repositories, and test configurations
- **Target Platforms**: Simics configurations, memory sizes, CPU counts, and features
- **Execution Parameters**: Performance model settings, cache configurations, and trace parameters
- **Results Data**: Execution logs, metrics, and performance counters

## 🚀 Quick Start

### Prerequisites
- Python 3.9 or higher
- Access to Intel Simulation Service (ISS) API
- AWS credentials for ISS authentication (managed via AWS Secrets Manager)
- AWS credentials for Bedrock AI integration (may be different account)
- Poetry or pip for dependency management

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/gabrielbriones/workload-analyzer.git
   cd workload-analyzer
   ```

2. **Install dependencies**:
   
   Using Poetry (recommended):
   ```bash
   poetry install
   ```
   
   Or using pip with requirements.txt:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   
   Copy and customize the environment template:
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials and configuration
   ```
   
   Or set environment variables directly:
   ```bash
   # ISS API configuration
   export ISS_API_URL="your-iss-api-endpoint"
   export AUTH_DOMAIN="your-auth-domain"
   export CLIENT_SECRET_NAME="your-iss-secret-name"
   
   # AWS credentials for ISS authentication (may be separate account)
   export AWS_ACCESS_KEY_ID_ISS="your-iss-aws-key"
   export AWS_SECRET_ACCESS_KEY_ISS="your-iss-aws-secret"
   export AWS_REGION_ISS="your-iss-aws-region"
   
   # AWS credentials for Bedrock AI integration
   export AWS_ACCESS_KEY_ID="your-bedrock-aws-key"
   export AWS_SECRET_ACCESS_KEY="your-bedrock-aws-secret"
   export AWS_REGION="us-east-1"
   
   # AI Model Configuration (optional)
   export BEDROCK_MODEL_ID="anthropic.claude-3-5-sonnet-20241022-v2:0"
   export BEDROCK_TEMPERATURE="0.7"
   export BEDROCK_MAX_TOKENS="4096"
   ```

4. **Enable Bedrock Model Access**:
   - Go to AWS Console → Amazon Bedrock
   - Navigate to "Model access" in the left sidebar
   - Request access to Claude, Titan, Llama, or other desired models
   - Wait for approval (usually instant)

5. **Run the application**:
   ```bash
   # Using Poetry
   poetry run uvicorn main:app --reload
   
   # Or using pip
   uvicorn main:app --reload
   ```

6. **Access the interfaces**:
   - **🤖 AI Chat Interface**: `http://localhost:8000/bedrock-chat/ui`
   - **📚 API Documentation**: `http://localhost:8000/docs`
   - **🔗 WebSocket Chat**: `ws://localhost:8000/bedrock-chat/ws`
   - **📊 API Health Check**: `http://localhost:8000/health`

## 📖 Usage Examples

### 🤖 AI Chat Interface Examples

#### **Platform and Job Discovery**
```
You: "Show me all available platforms that support IWPS workloads"

AI: I'll query the available platforms and check their IWPS support.

[AI calls GET /v1/platforms]
[AI calls GET /v1/jobs/iwps/{platform}/schema for each platform]

Found 5 platforms supporting IWPS:
- Intel-SPR-8380: SPR-based, 64GB RAM, supports advanced tracing
- Intel-ICL-1165G7: Ice Lake, 32GB RAM, optimized for mobile workloads  
- Intel-ADL-12700K: Alder Lake, 64GB RAM, hybrid architecture support
- Intel-RPL-13700K: Raptor Lake, 128GB RAM, latest generation features
- Intel-MTL-Ultra7: Meteor Lake, 32GB RAM, AI acceleration support

Would you like me to get the detailed schema for any specific platform?
```

#### **Job Status Monitoring**
```
You: "What's the status of job a2290337-a3d4-40db-904d-79222997688f and what files are available?"

AI: Let me check the details for that job and list available output files.

[AI calls GET /v1/jobs/job/a2290337-a3d4-40db-904d-79222997688f]
[AI calls GET /fs/files/a2290337-a3d4-40db-904d-79222997688f/iwps/artifacts/out]

Job Details:
- Job ID: a2290337-a3d4-40db-904d-79222997688f
- Status: complete
- Type: IWPS  
- Platform: Intel-SPR-8380
- Completed: 45 minutes ago
- Duration: 2 hours 18 minutes

Available Output Files:
✓ sim.out - Main simulation output log
✓ sim.summary.profile - Performance summary  
✓ cpi-stack.png - CPI stack visualization
✓ sim.memoryprofile - Memory access patterns
✓ sim.branchprofile - Branch prediction analysis
✓ sim.funcprofile - Function-level profiling
✓ sim.threads.profile - Multi-threading analysis

Would you like me to analyze any specific output file or generate a performance summary?
```

#### **File Analysis**
```
You: "Show me the contents of the simulation summary for job a2290337-a3d4-40db-904d-79222997688f"

AI: I'll retrieve the simulation summary file for you.

[AI calls GET /fs/files/a2290337-a3d4-40db-904d-79222997688f/iwps/artifacts/out/sim.summary.profile]

Simulation Summary:
- Total Instructions: 1,234,567,890
- Cycles: 987,654,321
- IPC: 1.25
- Cache Miss Rate (L1): 3.2%
- Cache Miss Rate (L2): 0.8%  
- Branch Prediction Accuracy: 94.6%
- Memory Bandwidth Utilization: 67%

Performance Insights:
🔍 Low IPC suggests potential optimization opportunities
🔍 L1 cache miss rate is within normal range
⚠️  Memory bandwidth could be better utilized

Would you like me to compare this with similar workloads or suggest optimizations?
```

#### **Schema Analysis**  
```
You: "What parameters can I configure for ISIM jobs on the SPR platform?"

AI: I'll get the ISIM schema for the Intel-SPR-8380 platform.

[AI calls GET /v1/jobs/isim/Intel-SPR-8380/schema]

Available ISIM Configuration Parameters:
- Core Frequency: 1.0-5.0 GHz (default: 3.2 GHz)
- Memory Configuration: DDR4/DDR5 support, up to 512GB
- Cache Settings: L1/L2/L3 configurable sizes and associativity
- Trace Collection: Event types, sampling rates, buffer sizes
- Performance Model: Detailed vs. Fast simulation modes
- Execution Parameters: Step count, warmup length, ROI settings

Would you like me to explain any specific parameter or suggest optimal settings?
```

#### **Platform Comparison**
```
You: "Compare simulation performance between SPR and ICL platforms for my workload"

AI: I'll analyze your workload performance across both platforms.

[AI calls /api/workloads/my-workload/performance?platforms=SPR,ICL]

Performance Comparison:
┌──────────────┬─────────────┬─────────────┬─────────────┐
│ Platform     │ Avg Runtime │ IPC         │ Memory BW   │
├──────────────┼─────────────┼─────────────┼─────────────┤
│ Intel SPR    │ 2.3 hours   │ 1.47        │ 245 GB/s    │
│ Intel ICL    │ 3.1 hours   │ 1.23        │ 198 GB/s    │
└──────────────┴─────────────┴─────────────┴─────────────┘

Recommendation: SPR platform is 26% faster for your workload due to:
- Higher memory bandwidth utilization
- Better branch prediction accuracy
- Optimized cache hierarchy for your access patterns
```

### 📊 Direct API Usage

#### **ISS API Integration (Read-Only)**
```python
# Platform Operations
response = requests.get("/v1/platforms")  # List all platforms
response = requests.get("/v1/platforms/platform/Intel-SPR-8380")  # Get platform details

# Job Monitoring (Job IDs are UUIDs with 'a' prefix, e.g., a2290337-a3d4-40db-904d-79222997688f)
response = requests.get("/v1/jobs")  # List all jobs
response = requests.get("/v1/jobs/job/a2290337-a3d4-40db-904d-79222997688f")  # Get specific job details

# Instance Management
response = requests.get("/v1/instances")  # List all instances
response = requests.get("/v1/instances/instance/inst-12345")  # Get instance details

# Schema Discovery
response = requests.get("/v1/jobs/iwps/Intel-SPR-8380/schema")  # IWPS schema for platform
response = requests.get("/v1/jobs/isim/Intel-ICL-1165G7/schema")  # ISIM schema for platform
response = requests.get("/v1/jobs/coho/Intel-SPR-8380/schema")  # Coho schema for platform

# File Service Operations (Different hostname)
response = requests.get("/fs/files/a2290337-a3d4-40db-904d-79222997688f/iwps/artifacts/out")  # List job output files
response = requests.get("/fs/files/a2290337-a3d4-40db-904d-79222997688f/iwps/artifacts/out/sim.out")  # Download specific file

# Performance Analysis (Workload Analyzer Extensions)
response = requests.get("/api/analysis/cache-performance?job_id=a2290337-a3d4-40db-904d-79222997688f")
response = requests.get("/api/analysis/platform-comparison?platforms=SPR,ICL")
response = requests.get("/api/metrics/job/a2290337-a3d4-40db-904d-79222997688f/summary")
```

## 🔧 Configuration

### ISS API Integration
The application uses AWS Secrets Manager to securely retrieve ISS API credentials. Configure your connection in `config.py`:

```python
import boto3
import json

def get_iss_credentials():
    """Retrieve ISS API credentials from AWS Secrets Manager"""
    client = boto3.client('secretsmanager', 
                         region_name=os.getenv('AWS_REGION_ISS'))
    
    secret_name = os.getenv('CLIENT_SECRET_NAME')
    response = client.get_secret_value(SecretId=secret_name)
    
    secret = json.loads(response['SecretString'])
    return {
        'client_id': secret['client_id'],
        'client_secret': secret['client_secret']
    }

def get_auth_token():
    """Generate authentication token using client credentials"""
    credentials = get_iss_credentials()
    auth_domain = os.getenv('AUTH_DOMAIN')
    
    # Token generation logic here
    # ... implementation details ...
    
    return access_token

ISS_CONFIG = {
    "base_url": os.getenv('ISS_API_URL'),
    "auth_domain": os.getenv('AUTH_DOMAIN'),
    "timeout": 30,
    "retry_attempts": 3
}
```

### Authentication Flow
1. **Secrets Retrieval**: Credentials are fetched from AWS Secrets Manager:
   ```bash
   aws secretsmanager get-secret-value --secret-id $CLIENT_SECRET_NAME | jq -cr '.SecretString'
   ```

2. **Token Generation**: Using `client_id` and `client_secret` to generate access tokens

3. **API Authentication**: Tokens are used to authenticate with ISS API endpoints

### AI Assistant Settings
The AI assistant is automatically configured through the auto-bedrock-chat-fastapi integration, which:

- **Auto-discovers API endpoints** and converts them to AI-callable tools
- **Creates real-time WebSocket chat** with conversation memory
- **Provides built-in web UI** at `/bedrock-chat/ui`
- **Handles session management** for concurrent users
- **Supports multiple AI models** from Amazon Bedrock

#### Model Configuration Options

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `BEDROCK_MODEL_ID` | `anthropic.claude-3-5-sonnet-20241022-v2:0` | AI model for workload analysis |
| `BEDROCK_TEMPERATURE` | `0.7` | Response creativity (0.0-1.0) |
| `BEDROCK_MAX_TOKENS` | `4096` | Maximum response length |
| `BEDROCK_MAX_TOOL_CALLS` | `10` | Maximum API calls per conversation |
| `BEDROCK_SESSION_TIMEOUT` | `3600` | Chat session timeout (seconds) |

#### Recommended Models for Intel Workloads

| Model | Best For | Performance |
|-------|----------|-------------|
| **Claude 4.5 Sonnet** | Complex analysis, technical reasoning | 🚀 **Most capable** |
| **Claude 3.5 Sonnet** | General workload analysis | ⚡ **Balanced** |
| **Claude 3.5 Haiku** | Quick queries, cost optimization | 💰 **Fast & economical** |
| **OpenAI GPT OSS** | Open-source transparency | 🌐 **Enterprise-friendly** |

#### Security & Access Control

```python
# Configure which endpoints AI can access
add_bedrock_chat(
    app,
    bedrock_model_id="anthropic.claude-3-5-sonnet-20241022-v2:0",
    aws_region="us-east-1",
    
    # Control AI access to endpoints
    allowed_paths=["/api/jobs", "/api/metrics", "/api/platforms"],
    excluded_paths=["/admin", "/internal", "/sensitive"],
    
    # Custom system prompt for Intel workloads
    custom_system_prompt="""
    You are an expert Intel simulation workload analyst. 
    Help users optimize their IWPS, ISIM, and simulation jobs.
    Focus on performance analysis, configuration tuning, and troubleshooting.
    Always explain your reasoning and cite specific metrics when available.
    """
)
- Handles context management for workload discussions
- Provides domain-specific knowledge for Intel simulation workloads

## 📁 Project Structure

```
workload-analyzer/
├── README.md              # This file
├── schema_jobs.json       # Complete job data schema
├── pyproject.toml         # Poetry dependency management
├── requirements.txt       # Pip dependency management (alternative)
├── main.py               # FastAPI application (to be created)
```
workload-analyzer/
├── README.md              # This file
├── schema_jobs.json       # Complete job data schema
├── pyproject.toml         # Poetry dependency management
├── requirements.txt       # Pip dependency management (alternative)
├── .env.example           # Environment configuration template
├── main.py               # FastAPI application (to be created)
├── models/               # Data models and schemas
├── services/             # ISS API integration services
├── analysis/             # AI analysis modules
├── config.py             # Configuration management
└── tests/                # Unit and integration tests
```

## 🤝 Contributing

We welcome contributions! Please see our contributing guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 🆘 Support

For support and questions:

- **Issues**: Use GitHub Issues for bug reports and feature requests
- **Documentation**: Check the `/docs` endpoint when running the application
- **Intel ISS**: Refer to Intel Simulation Service documentation for API details

---

**Note**: This project requires access to Intel Simulation Service (ISS) and is designed for Intel architecture simulation workflows.