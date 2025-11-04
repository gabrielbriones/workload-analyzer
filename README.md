# Workload Analyzer

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://python.org)
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
- **Optimization Recommendations**: Get specific suggestions for improving workload efficiency
- **Configuration Tuning**: Receive guidance on optimal simulation parameters
- **Compilation Analysis**: Insights into build process improvements

### Integration Capabilities
- **RESTful API**: Clean, documented endpoints for all workload operations
- **OpenAPI Specification**: Auto-generated API documentation and tool definitions
- **Chat Interface**: Built-in conversational UI for interactive analysis
- **Extensible Architecture**: Easy to add new analysis modules and data sources

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
- Python 3.8 or higher
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
   ```

4. **Run the application**:
   ```bash
   uvicorn main:app --reload
   ```

5. **Access the interface**:
   - API Documentation: `http://localhost:8000/docs`
   - Chat Interface: `http://localhost:8000/chat`

## 📖 Usage Examples

### Query Job Status
```python
# Get all jobs for a specific workload
response = requests.get("/api/jobs?workload_id=my-workload")

# Check execution status
response = requests.get("/api/jobs/12345/status")
```

### AI Assistant Queries
- "What's the performance bottleneck in my SPEC CPU workload?"
- "How can I optimize the cache configuration for better IPC?"
- "Why is my simulation taking longer than expected?"
- "Compare the performance between these two platform configurations"

### Performance Analysis
```python
# Get performance metrics for a completed job
response = requests.get("/api/jobs/12345/metrics")

# Analyze cache miss rates
response = requests.get("/api/analysis/cache-performance?job_id=12345")
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

- Generates tool definitions from the OpenAPI specification
- Creates a conversational interface
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