# Callio_Labs — Agentic Genome Research Platform

Devpost https://devpost.com/software/callio-labs
An AI-powered genomics research platform by **Callio Labs** that combines a multi-persona mutation research chatbot, DNA primer design, NCBI dataset integration, protein structure prediction, and a visual LangFlow agent — all behind a modern Next.js dashboard with 3D DNA visualization.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Project Structure](#project-structure)
- [Backend](#backend)
  - [Mutation Research Chat Agent](#mutation-research-chat-agent)
  - [Primer3 Design Service](#primer3-design-service)
  - [NCBI Datasets MCP Server](#ncbi-datasets-mcp-server)
  - [LangFlow Genome Primer Design Agent](#langflow-genome-primer-design-agent)
- [Frontend](#frontend)
- [ColabFold on Modal](#colabfold-on-modal)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [ColabFold Setup](#colabfold-setup)
- [Environment Variables](#environment-variables)
- [API Reference](#api-reference)
- [Tech Stack](#tech-stack)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js Frontend                     │
│  Landing Page · Dashboard · Chatbot Panel · 3D DNA     │
│  Google OAuth (NextAuth)                                │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP
┌────────────────────────▼────────────────────────────────┐
│               FastAPI Backend (main app)                │
│  POST /api/v1/chat          → LangGraph mutation agent  │
│  POST /api/v1/design-from-alignment → Primer3 proxy    │
│  /primer3/*                 → Primer3 service           │
└───┬──────────────┬──────────────┬───────────────────────┘
    │              │              │
    ▼              ▼              ▼
┌────────┐  ┌───────────┐  ┌──────────────┐
│ Primer3│  │ NCBI MCP  │  │ ColabFold on │
│ Service│  │  Server   │  │    Modal      │
│ :8001  │  │  :8000    │  │  (GPU cloud)  │
└────────┘  └───────────┘  └──────────────┘
```

---

## Project Structure

```
GenaiGenesis2026/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app — chat endpoint & Primer3 proxy
│   │   └── config.py                  # Pydantic settings & LLM configuration
│   ├── primer3_service/
│   │   ├── main.py                    # Primer3 FastAPI microservice
│   │   ├── design.py                  # Primer design logic
│   │   ├── schemas.py                 # Request/response models
│   │   └── simple_primer_design.py    # Simplified design helpers
│   ├── unofficial_ncbi_mcp/
│   │   ├── server.py                  # FastMCP server (NCBI Datasets API)
│   │   ├── client.py                  # NCBI Datasets HTTP client
│   │   └── README.md
│   ├── generate_langflow_json.py      # Generates LangFlow-compatible flow JSON
│   ├── Genome Primer Design Agent FINAL.json  # LangFlow flow definition
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── app/
│   │   ├── layout.tsx                 # Root layout
│   │   ├── page.tsx                   # Landing page
│   │   ├── api/auth/[...nextauth]/    # NextAuth route handler
│   │   └── dashboard/
│   │       ├── page.tsx               # Dashboard page
│   │       └── dashboard-content.tsx  # Dashboard components
│   ├── components/
│   │   ├── chatbot-panel.tsx          # Chat UI with model selector
│   │   ├── landing-page.tsx           # Landing page content
│   │   ├── dna-viewer.tsx             # 3D DNA model (Three.js)
│   │   ├── Dither.jsx                 # Dither effect background
│   │   ├── callio-labs-splash.tsx      # Splash screen
│   │   ├── site-header.tsx
│   │   ├── app-sidebar.tsx
│   │   └── ui/                        # shadcn/Radix UI components
│   ├── auth.ts                        # NextAuth configuration (Google OAuth)
│   ├── types/human_dna.glb            # 3D DNA model asset
│   ├── package.json
│   └── .env.example
├── colabfold_modal/
│   ├── app.py                         # ColabFold/AlphaFold2 on Modal GPUs
│   ├── requirements.txt
│   └── README.md
└── mutation-agent.chat.plan.md        # Build plan for mutation research agent
```

---

## Backend

### Mutation Research Chat Agent

A **LangGraph**-based multi-persona chatbot that researches genetic mutations using a fan-out/fan-in architecture:

1. **Search Agent** — queries PubMed, bioRxiv, gnomAD, and ClinVar for evidence.
2. **5 Parallel Persona Agents** — each analyzes the evidence from a different domain:
   - **Clinical Agent** — disease risk and clinical significance
   - **Neuro Agent** — neurological and neurotransmitter impact
   - **Pharmacogenomics Agent** — drug response and metabolism
   - **Structural Agent** — protein structure and function effects
   - **Data Science Agent** — statistical patterns and population data
3. **Judge Agent** — ranks hypotheses by evidence strength and consistency.
4. **Quality Check** — loops back to search if evidence is insufficient (up to a configurable max iterations).
5. **Response Composer** — produces a structured final answer with citations, limitations, and supporting hypotheses.

The system is **LLM-provider-agnostic** — a factory function (`get_chat_model`) returns LangChain-compatible model instances, configurable per purpose (search, hypothesis, judge, response) via environment variables.

**Run:**

```bash
cd backend
uvicorn app.main:app --reload
```

### Primer3 Design Service

A standalone FastAPI microservice wrapping [primer3-py](https://github.com/libnano/primer3-py). Accepts up to 3 DNA sequences and returns 3 primer pairs per sequence with full statistics (Tm, GC%, product size, penalty, etc.).

**Run:**

```bash
cd backend
uvicorn primer3_service.main:app --reload --port 8001
```

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Liveness check |
| POST | `/design` | Design primers from sequences |

### NCBI Datasets MCP Server

A [FastMCP](https://github.com/jlowin/fastmcp) server that exposes the [NCBI Datasets API](https://www.ncbi.nlm.nih.gov/datasets/) as MCP tools and resources for use in AI agents and IDE integrations (e.g., Cursor).

**Tools:** `search_genomes`, `get_genome_info`, `search_genes`, `get_gene_info`, `search_taxonomy`, `get_taxonomy_info`, `search_assemblies`, `get_assembly_info`, and more.

**Resources:** `ncbi://genome/{accession}`, `ncbi://gene/{gene_id}`, `ncbi://taxonomy/{tax_id}`, etc.

**Run (stdio — for IDE MCP):**

```bash
cd backend
python -m unofficial_ncbi_mcp
```

**Run (HTTP — for remote clients):**

```bash
cd backend
MCP_TRANSPORT=http python -m unofficial_ncbi_mcp
```

Listens on `http://127.0.0.1:8000` by default (configurable via `MCP_HOST` / `MCP_PORT`).

### LangFlow Genome Primer Design Agent

`Genome Primer Design Agent FINAL.json` is a large LangFlow flow (16,000+ lines) that defines a visual agent for genome primer design. It includes ChatInput nodes, Prompt Templates, AI Agents, MCP tool integrations, and output nodes.

**Generate updated flow JSON:**

```bash
cd backend
python generate_langflow_json.py
```

---

## Frontend

A **Next.js 15** application (React 19) with:

- **Landing Page** — animated dither background, interactive 3D DNA helix (Three.js / React Three Fiber), Callio Labs branding, and Google sign-in.
- **Dashboard** — sidebar navigation, header, section cards, and data tables.
- **Chatbot Panel** — conversational interface with model selector (Claude, OpenAI, Gemini, DeepSeek) that connects to the backend chat API.
- **Authentication** — Google OAuth via NextAuth v5.
- **UI Components** — built with shadcn/ui and Radix UI primitives, styled with Tailwind CSS 4.

**Run:**

```bash
cd frontend
npm install
npm run dev
```

The dev server starts at `http://localhost:3000`.

---

## ColabFold on Modal

Runs [ColabFold](https://github.com/sokrypton/ColabFold) (AlphaFold2 + MMseqs2) on [Modal](https://modal.com) GPUs for protein structure prediction, exposed as an HTTP endpoint.

**Endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| POST | `/predict` | Submit a protein sequence for structure prediction |
| GET | `/health` | Health check |

**Request body (`/predict`):**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `sequence` | string | Yes | Protein sequence (one-letter codes) or FASTA. Use `:` between chains for complexes. |
| `job_name` | string | No | Job identifier (default `"query"`) |
| `num_models` | int | No | Number of AlphaFold models, 1–5 (default 1) |

**Response:** PDB structure (text and base64), scores/metadata JSON, optional confidence plot (base64 PNG).

**Run:**

```bash
cd colabfold_modal
pip install modal
modal token new          # one-time auth
modal run app.py         # local test
modal serve app.py       # ephemeral URL
modal deploy app.py      # persistent endpoint
```

---

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** and npm
- (Optional) [Modal](https://modal.com) account for ColabFold
- (Optional) [NCBI API Key](https://www.ncbi.nlm.nih.gov/account/) for higher rate limits
- Google OAuth credentials for frontend auth

### Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env   # or create .env with required variables (see below)

# Start the main API server
uvicorn app.main:app --reload

# (In a separate terminal) Start the Primer3 service
uvicorn primer3_service.main:app --reload --port 8001
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env.local
# Fill in AUTH_SECRET, AUTH_GOOGLE_ID, AUTH_GOOGLE_SECRET

# Start development server
npm run dev
```

### ColabFold Setup

```bash
cd colabfold_modal
pip install modal
modal token new
modal serve app.py
```

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `NCBI_API_KEY` | NCBI API key for higher rate limits | — |
| `NCBI_BASE_URL` | NCBI Datasets API base URL | `https://api.ncbi.nlm.nih.gov/datasets/v2` |
| `MCP_TRANSPORT` | MCP transport mode: `stdio` or `http` | `stdio` |
| `MCP_HOST` | MCP HTTP host | `127.0.0.1` |
| `MCP_PORT` | MCP HTTP port | `8000` |
| `APP_LLM_PROVIDER` | LLM provider (`openai`, `anthropic`, `ollama`, `fake`) | `fake` |
| `APP_LLM__MODEL_NAME` | Default model name | `default` |
| `APP_LLM__TEMPERATURE` | LLM temperature | `0.3` |
| `APP_LLM__MAX_TOKENS` | Max generation tokens | `2048` |
| `APP_DEFAULT_MAX_ITERATIONS` | Max quality-check loop iterations | `3` |
| `APP_MOCK_RETRIEVAL` | Use mock retrieval data | `True` |
| `APP_PRIMER3_BASE_URL` | Primer3 service URL | `http://127.0.0.1:8001` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|----------|-------------|---------|
| `AUTH_SECRET` | NextAuth secret (generate with `npx auth secret`) | — |
| `AUTH_URL` | Application base URL | `http://localhost:3000` |
| `AUTH_GOOGLE_ID` | Google OAuth client ID | — |
| `AUTH_GOOGLE_SECRET` | Google OAuth client secret | — |

---

## API Reference

### Main Backend (`http://localhost:8000`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/chat` | Submit a mutation research query to the LangGraph agent |
| POST | `/api/v1/design-from-alignment` | Design primers from a sequence alignment |
| * | `/primer3/*` | Proxy to the Primer3 microservice |

### Primer3 Service (`http://localhost:8001`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| POST | `/design` | Design primers from DNA sequences |

### NCBI MCP Server (`http://localhost:8000/mcp`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Service info |
| GET | `/health` | Health check |
| POST | `/mcp` | MCP Streamable HTTP (JSON-RPC initialize first) |

### ColabFold on Modal

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/predict` | Predict protein structure from sequence |
| GET | `/health` | Health check |

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Frontend** | Next.js 15, React 19, TypeScript 5, Tailwind CSS 4, shadcn/ui, Radix UI, Three.js, React Three Fiber, NextAuth v5, Recharts, Zod |
| **Backend** | Python 3.10+, FastAPI, LangGraph, LangChain, Pydantic v2, httpx, uvicorn, primer3-py, FastMCP |
| **Protein Prediction** | ColabFold (AlphaFold2 + MMseqs2), Modal (serverless GPUs) |
| **External APIs** | NCBI Datasets, PubMed, bioRxiv, gnomAD, ClinVar |
| **Auth** | Google OAuth 2.0 |
