# LLM Simulation Service

A specialized service for testing and optimizing multi-agent conversational AI systems through scalable simulation and automated evaluation.

## Overview

This service enables systematic testing of multi-agent systems (MAS) by simulating conversations between multiple specialized agents (sales, support, etc.) and scripted clients, followed by automated quality evaluation. Built specifically to solve the lack of ready-to-use solutions for testing multi-agent conversational AI infrastructure.

### Key Features

- **Multi-Agent Conversations**: Support for dynamic agent handoffs during conversations
- **Scalable Batch Processing**: Parallel execution of thousands of test scenarios  
- **Deterministic Testing**: Reproducible results using consistent seeds and prompts
- **Prompt Engineering Support**: File-based prompt management with validation
- **Comprehensive Evaluation**: Automated scoring with detailed feedback
- **Multiple Interfaces**: REST API and CLI for different workflows

## Purpose of this Codebase

This service was created to address the specific need for testing multi-agent systems where:

- **No existing solutions** fit our infrastructure requirements
- **Prompt optimization** requires systematic testing across many scenarios
- **Multi-agent coordination** needs evaluation (handoffs, context preservation)
- **Scale testing** demands parallel execution capabilities
- **Quality assurance** requires automated, consistent evaluation

The service enables QA teams and prompt engineers to validate conversational AI systems before deployment, ensuring agent coordination works correctly and prompts perform as expected across diverse scenarios.

## Architecture

```mermaid
graph TB
    subgraph "Presentation Layer"
        API[REST API<br/>main.py]
        
        API --> |HTTP Routes| BR[Batch Routes]
        API --> |HTTP Routes| PR[Prompt Routes] 
        API --> |HTTP Routes| UR[User Routes]
    end
    
    subgraph "Service Layer"
        CE[Conversation Engine<br/>autogen_conversation_engine.py]
        BP[Batch Processor<br/>batch_processor.py]
        EV[Evaluator<br/>evaluator.py]
        PS[Prompt Specification<br/>prompt_specification.py]
        TS[Tools Specification<br/>tools_specification.py]
        
        CE --> |orchestrates| MA[Multi-Agent<br/>Conversations]
        BP --> |manages| CE
        BP --> |scores with| EV
    end
    
    subgraph "Infrastructure Layer"
        OW[OpenAI Wrapper<br/>openai_wrapper.py]
        PST[Persistent Storage<br/>persistent_storage.py]
        RS[Result Storage<br/>result_storage.py]
        TE[Tool Emulator<br/>tool_emulator.py]
        WM[Webhook Manager<br/>webhook_manager.py]
        LU[Logging Utils<br/>logging_utils.py]
    end
    
    subgraph "External Dependencies"
        OPENAI[OpenAI API]
        FS[File System]
        WH[External Webhooks]
        EXT_API[External Tool APIs<br/>aiwingg.com/rag]
    end
    
    %% Layer connections
    BR --> BP
    PR --> PS
    BP --> CE
    BP --> EV
    CE --> OW
    CE --> TE
    CE --> WM
    BP --> PST
    BP --> RS
    PS --> FS
    
    %% External connections
    OW --> OPENAI
    EV --> OPENAI
    PST --> FS
    RS --> FS
    WM --> WH
    TE --> EXT_API
    LU --> FS
    
    %% Styling
    classDef presentation fill:#e1f5fe
    classDef service fill:#f3e5f5  
    classDef infrastructure fill:#e8f5e8
    classDef external fill:#fff3e0
    
    class API,BR,PR,UR presentation
    class CE,BP,EV,PS,TS,MA service
    class OW,PST,RS,TE,WM,LU infrastructure
    class OPENAI,FS,WH,EXT_API external
```

**Architecture Principles:**
- **Presentation Layer**: Handles user interfaces and API endpoints
- **Service Layer**: Contains business logic for simulation orchestration
- **Infrastructure Layer**: Manages external dependencies and data persistence

## Documentation

### Setup & Usage
- [Configuration System](docs/configuration/config_system.md) - Environment variables, settings, validation
- [Deployment Guide](docs/deployment/deployment_guide.md) - Docker setup, environment configuration
- [Scripts Overview](docs/scripts_overview.md) - CLI tools and their interfaces

### Architecture Deep Dive
- [Presentation Layer](docs/layers/presentation_layer.md) - API routes, request handling, validation
- [Service Layer](docs/layers/service_layer.md) - Business logic, workflow orchestration
- [Infrastructure Layer](docs/layers/infrastructure_layer.md) - External integrations, storage adapters
- [Modules Overview](docs/modules_overview.md) - Complete file-to-layer mapping

### API & Contracts
- [HTTP API Reference](docs/contracts/http_api_openapi.yaml) - Complete OpenAPI specification
- [Service Contracts](docs/contracts/service_layer_contracts/) - Internal service interfaces
- [Storage Contracts](docs/contracts/storage_contracts/) - Data persistence interfaces
- [Infrastructure Contracts](docs/contracts/infra_util_contracts/) - External adapter contracts
