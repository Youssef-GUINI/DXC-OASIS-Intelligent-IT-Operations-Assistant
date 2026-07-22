# OASIS AI Copilot
### Intelligent IT Operations Assistant

## Project Overview

OASIS AI Copilot is an AI-powered IT Operations Assistant developed during a PFA internship at DXC Technology.

The objective is to build a multi-agent platform capable of assisting Linux Engineers and Storage & Backup Engineers in incident resolution, root cause analysis, infrastructure monitoring, and report generation.

The architecture is based on:

- FastAPI
- PostgreSQL
- Docker
- ChromaDB
- MCP (Model Context Protocol)
- LangChain
- Multi-Agent Architecture
- LLM Router (Groq / Claude)
- JWT Authentication
- Role-Based Access Control (RBAC)

---

# Current Project Status

Current Version:

**Architecture Freeze V1**

Completed Progress:

- ✅ Step 1 – Project Initialization
- ✅ Step 2 – Authentication & Security

---

# Architecture

```
Users
   │
   ▼
FastAPI API
   │
   ▼
Authentication (JWT)
   │
   ▼
Orchestrator
   │
   ▼
LLM Router
   │
   ├── Linux Persona
   │
   └── Storage Persona
          │
          ▼
      MCP Servers
          │
          ▼
 Linux Infrastructure
 Storage Infrastructure
```

---

# Technology Stack

## Backend

- Python 3.13
- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Docker
- JWT Authentication
- Pydantic

## AI

- Groq API
- Anthropic Claude
- LangChain
- ChromaDB
- Sentence Transformers

## Frontend

- React
- Vite
- TailwindCSS

---

# Current Folder Structure

```
backend/
frontend/
docs/
.github/
docker-compose.yml
README.md
```

---

# Step 1 — Project Initialization

## Objectives

Prepare the complete development environment before implementing business logic.

### Completed

- Project architecture created
- Backend structure
- Frontend structure
- Documentation folders
- Virtual Environment
- Git repository
- Docker environment
- PostgreSQL container
- ChromaDB container
- Python dependencies
- requirements.txt

### Docker Services

Running containers:

- PostgreSQL
- ChromaDB

---

# Step 2 — Authentication & Security

Objective:

Implement a complete authentication system before developing AI features.

## Implemented

### Database

- PostgreSQL
- SQLAlchemy ORM
- Alembic migrations

### Tables

- users
- roles
- alembic_version

### Roles

- linux_engineer
- storage_engineer
- administrator

### Default Users

Linux Engineer

```
linux@oasis.com
```

Storage Engineer

```
storage@oasis.com
```

Administrator

```
admin@oasis.com
```

### Security

Implemented:

- JWT Authentication
- Password Hashing (bcrypt)
- Token Validation
- Role-Based Access Control (RBAC)

### API Endpoints

POST

```
/api/v1/auth/login
```

GET

```
/api/v1/auth/me
```

---

# Tests Completed

Successfully validated:

- FastAPI server
- Swagger documentation
- PostgreSQL connection
- Docker containers
- Alembic migrations
- Login endpoint
- JWT generation
- Protected endpoint
- Role verification
- User retrieval

---

# Database Status

Current tables:

- users
- roles
- alembic_version

Current roles:

- Linux Engineer
- Storage Engineer
- Administrator

Current users:

- linux@oasis.com
- storage@oasis.com
- admin@oasis.com

---

# Next Step

Step 3

Persona Layer

Implementation of:

- Linux Persona
- LLM Router
- Groq Client
- Claude Client
- Linux Chat Endpoint

Pipeline:

```
User

↓

Linux API

↓

Orchestrator

↓

LLM Router

↓

Linux Persona

↓

LLM

↓

Response
```

---

# Long-Term Roadmap

- Authentication
- Persona Layer
- LLM Router
- RAG Integration
- ChromaDB Knowledge Base
- MCP Client
- MCP Servers
- Linux Tools
- Storage Tools
- Cross-Domain Access
- Dashboard
- Reports
- Metrics
- Deployment

---

# Authors

PFA Internship

DXC Technology

Project:

OASIS AI Copilot — Intelligent IT Operations Assistant