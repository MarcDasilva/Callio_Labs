---
name: mutation-agent-chat-build-plan
overview: Build a Python + FastAPI LangGraph-based multi-persona mutation research chatbot using a fan-out/fan-in architecture with a provider-agnostic LLM layer.
todos:
  - id: project-scaffold
    content: Set up backend project structure and dependencies for the chat agent.
    status: pending
  - id: define-schemas
    content: Implement Pydantic models for chat inputs, intermediate evidence objects, and chat responses.
    status: pending
  - id: define-state
    content: Define LangGraph state model and shared types for multi-turn chat.
    status: pending
  - id: implement-llm-abstraction
    content: Implement provider-agnostic ChatModel factory and configuration.
    status: pending
  - id: implement-retrieval-layer
    content: Implement retrieval interfaces for PubMed, bioRxiv, gnomAD, ClinVar (stubs or real) usable from chat.
    status: pending
  - id: implement-nodes
    content: Implement all LangGraph node functions (search, persona agents, judge, quality check, response composer).
    status: pending
  - id: build-graph
    content: Assemble and compile the LangGraph topology with fan-out/fan-in and quality-check loop.
    status: pending
  - id: fastapi-chat-api
    content: Expose the graph via a FastAPI /chat endpoint for frontend integration.
    status: pending
  - id: testing-strategy
    content: Add tests for schemas, nodes, and end-to-end chat flows.
    status: pending
  - id: observability-ops
    content: Add logging, configuration, and basic ops considerations for the chat agent.
    status: pending
isProject: true
---

## 1. Goal & Context

- **Goal**: Implement the agentic AI mutation research workflow from `workflow.md` as a **Python + FastAPI** backend that uses **LangGraph** to orchestrate:
  - A **Search Agent**.
  - **5 parallel persona agents** (clinical, neuro, pharmacogenomics, structural, data science).
  - A **Judge** with a **QualityCheck** loop.
  - A **response composer** that returns a structured chat answer.
- **LLM Design**: The system must be **LLM-provider-agnostic**, using a single abstraction layer that returns LangChain-compatible `ChatModel` instances, so any provider can be plugged in later.

## 2. Project Structure

- **Target layout** (under `backend/`):
  - `app/`
    - `main.py` – FastAPI app, routes, startup wiring.
    - `config.py` – environment variables, settings (model configs, API keys, loop limits).
    - `schemas.py` – Pydantic models for:
      - `UserQuery` (chat input)
      - `SearchResult`
      - `Hypothesis`
      - `JudgeDecision`
      - `ChatResponse`
    - `graph/`
      - `state.py` – LangGraph state definition and shared types.
      - `nodes/`
        - `search_agent.py`
        - `clinical_agent.py`
        - `neuro_agent.py`
        - `pharmacogenomics_agent.py`
        - `structural_agent.py`
        - `datascience_agent.py`
        - `judge_agent.py`
        - `quality_check.py`
        - `response_composer.py`
      - `graph_builder.py` – constructs and compiles the LangGraph.
    - `llm/`
      - `base.py` – provider-agnostic `get_chat_model(purpose: str)` and config structures.
    - `services/`
      - `retrieval.py` – interfaces and concrete implementations for PubMed, bioRxiv, gnomAD, ClinVar (can start as stubs).
    - `logging_config.py` – basic structured logging configuration.
  - `tests/`
    - `test_schemas.py`
    - `test_graph_paths.py`
    - `test_nodes_search.py`, `test_nodes_personas.py`, `test_nodes_judge.py`, etc.
  - `requirements.txt` – Python dependencies (LangGraph, LangChain, FastAPI, Pydantic, httpx, uvicorn, etc.).

## 3. Data & API Design

### 3.1 Input Schema (`schemas.py`)

- **`UserQuery`**
  - `query_text: str` – user’s core question (e.g., “Impact of MTHFR C677T on neurotransmitters”).
  - `mutation_ids: list[str] | None` – optional mutation identifiers.
  - `phenotype_hints: list[str] | None` – optional phenotypic context.
  - `max_iterations: int | None` – optional override of default QualityCheck loop cap.
  - `history: list[str] | None` – optional prior chat turns if you want basic conversational context.

### 3.2 Intermediate Schemas

- **`SearchResult`**
  - `source: Literal["pubmed","biorxiv","gnomad","clinvar","other"]`
  - `title: str`
  - `authors: list[str] | None`
  - `year: int | None`
  - `url: str | None`
  - `abstract: str | None`
  - `variant_annotations: dict | None`
  - `evidence_score: float | None`

- **`Hypothesis`**
  - `agent_id: Literal["clinical","neuro","pharmacogenomics","structural","datascience"]`
  - `summary: str`
  - `mechanism: str | None`
  - `risk_assessment: str | None`
  - `recommendations: str | None`
  - `confidence: float`
  - `citations: list[str]`

- **`JudgeDecision`**
  - `ranked_hypotheses: list[Hypothesis]`
  - `selected_index: int`
  - `reasoning: str`
  - `meets_threshold: bool`

### 3.3 Output Schema

- **`ChatResponse`**
  - `answer: str` – final natural-language answer returned to the user.
  - `supporting_hypotheses: list[Hypothesis]` – ordered list of hypotheses (judge-ranked).
  - `iterations_used: int`
  - `limitations: str`
  - `sources: list[str]`

- **FastAPI Endpoint** (conceptual):
  - `POST /api/v1/chat` → body: `UserQuery` → response: `ChatResponse`.

## 4. LangGraph State & Topology

### 4.1 State Model (`graph/state.py`)

- Define a typed state for LangGraph:
  - `user_query: UserQuery`
  - `search_results: list[SearchResult]`
  - `hypotheses: list[Hypothesis]`
  - `judge_decision: JudgeDecision | None`
  - `iterations: int`
  - `max_iterations: int`

### 4.2 Nodes (from `workflow.md` personas)

- `SearchAgent` (Researcher).
- `ClinicalAgent` (Agent 2a).
- `NeuroAgent` (Agent 2b).
- `PharmacogenomicsAgent` (Agent 2c).
- `StructuralAgent` (Agent 2d).
- `DataScienceAgent` (Agent 2e).
- `JudgeAgent` (Chief Scientist).
- `QualityCheckNode` (threshold decision).
- `ResponseComposerNode` (final chat response).

### 4.3 Graph Topology

- Flow matching the fan-out/fan-in and loop:
  - `UserInput` (injected from API) → `SearchAgent`
  - `SearchAgent` → **parallel**:
    - `ClinicalAgent`
    - `NeuroAgent`
    - `PharmacogenomicsAgent`
    - `StructuralAgent`
    - `DataScienceAgent`
  - All persona nodes → `JudgeAgent`
  - `JudgeAgent` → `QualityCheckNode`
  - `QualityCheckNode`:
    - If `meets_threshold == True`: → `ResponseComposerNode`
    - Else, if `iterations < max_iterations`: → `SearchAgent` (loop)
    - Else: → `ResponseComposerNode` (best-effort, low-confidence path)
- Represent this topology in `graph_builder.py` using LangGraph primitives and enabling concurrency for the persona nodes.

## 5. LLM Abstraction Layer (`llm/base.py`)

- Implement a **provider-agnostic** factory:
  - `get_chat_model(purpose: str) -> ChatModel`
    - `purpose` values: `"search"`, `"hypothesis"`, `"judge"`, `"response"`.
    - Reads configuration from `config.py` (model names, temperature, context window, etc.).
    - Returns a LangChain-compatible `ChatModel` instance without exposing provider specifics to calling code.
- Define a minimal configuration structure:
  - `LLMConfig` (e.g., `model_name`, `temperature`, `max_tokens`, `timeout`).
  - Map `purpose` to `LLMConfig` in `config.py`.
- All nodes import only `get_chat_model` and never depend on provider-specific features.

## 6. Retrieval Layer (`services/retrieval.py`)

- Define interfaces (can initially be stubs; concrete implementations added later):
  - `search_pubmed(query: str) -> list[SearchResult]`
  - `search_biorxiv(query: str) -> list[SearchResult]`
  - `query_gnomad(mutation_ids: list[str]) -> list[SearchResult]`
  - `query_clinvar(mutation_ids: list[str]) -> list[SearchResult]`
- Internally use `httpx` or similar HTTP client.
- Implement minimal error handling and timeouts.
- Normalize external responses into `SearchResult` objects.
- In initial iterations, allow “mock mode” (e.g., environment flag) to return synthetic data for tests and local development.

## 7. Node Implementations (`graph/nodes/*.py`)

### 7.1 `search_agent.py`

- Inputs: `state.user_query`, `state.search_results`.
- Steps:
  - Build search queries from `UserQuery` (combine `query_text`, `mutation_ids`, `phenotype_hints`).
  - Call retrieval services to fetch updated results.
  - Merge with existing `search_results` (optionally deduplicate).
- Outputs: updated `state.search_results`.

### 7.2 Persona Nodes

- Files: `clinical_agent.py`, `neuro_agent.py`, `pharmacogenomics_agent.py`, `structural_agent.py`, `datascience_agent.py`.
- Each node:
  - Inputs: `state.user_query`, `state.search_results`.
  - Use `get_chat_model("hypothesis")`.
  - Prompt pattern:
    - System: role description (e.g., Clinical Expert, focus: disease risk).
    - Instructions:
      - Use only evidence from `search_results`.
      - Output must match `Hypothesis` JSON schema.
      - Provide citations by URL or reference ID.
  - Parse the LLM output into a `Hypothesis` with the correct `agent_id`.
- Outputs: update `state.hypotheses` with that persona’s hypothesis.

### 7.3 `judge_agent.py`

- Inputs: `state.hypotheses`, `state.search_results`.
- Use `get_chat_model("judge")`.
- Prompt:
  - Compare hypotheses.
  - Rank by evidence strength, internal consistency, safety.
  - Decide if evidence meets a pre-defined scientific threshold.
- Outputs:
  - Set `state.judge_decision` with:
    - `ranked_hypotheses`
    - `selected_index`
    - `reasoning`
    - `meets_threshold`.

### 7.4 `quality_check.py`

- Inputs: `state.judge_decision`, `state.iterations`, `state.max_iterations`.
- Logic:
  - If `judge_decision.meets_threshold` is `True` → route to `ResponseComposerNode`.
  - Else if `iterations < max_iterations`:
    - Increment `state.iterations`.
    - Route back to `SearchAgent`.
  - Else:
    - Route to `ResponseComposerNode` with an implied “best-effort, insufficient evidence” state.

### 7.5 `response_composer.py`

- Inputs: `state.judge_decision`, `state.hypotheses`, `state.user_query`, `state.search_results`.
- Compose the final **chat response**:
  - Use the selected hypothesis as the primary basis for the answer.
  - Include remaining hypotheses as supporting or alternative views where useful.
  - Derive a concise answer string, limitations, and sources from hypotheses and citations.
- Output: map state into a `ChatResponse` instance returned via FastAPI.

## 8. Graph Assembly (`graph/graph_builder.py`)

- Define LangGraph nodes bound to the functions in `nodes/`.
- Declare edges as per the topology in Section 4.
- Enable parallel execution for persona nodes.
- Configure error handling:
  - Retries for transient retrieval/LLM failures.
  - Fallback behavior (e.g., drop a failing persona and continue if others succeed).
- Compile the graph at startup:
  - Provide a `get_compiled_graph()` function reused by FastAPI.

## 9. FastAPI Integration (`app/main.py`)

- Create `FastAPI()` application instance.
- On startup:
  - Initialize configuration.
  - Initialize or cache compiled graph instance.
- Define endpoint:
  - `POST /api/v1/chat`
    - Parse `UserQuery`.
    - Initialize state (`iterations=0`, `max_iterations` from query or default).
    - Run the compiled graph.
    - Convert final state into `ChatResponse`.
- Add basic error handlers (validation errors, external service failures).

## 10. Testing & Observability

- **Testing**:
  - Unit tests for:
    - `schemas.py` (model validation).
    - `services/retrieval.py` (mocked HTTP).
    - Node functions with mocked LLM and retrieval layers.
  - Integration tests:
    - End-to-end chat execution on synthetic `UserQuery`.
    - QualityCheck loop scenarios (sufficient vs insufficient evidence).
- **Observability**:
  - Logging:
    - Trace IDs for requests.
    - Node-level timings and errors.
  - Configuration:
    - All secrets and endpoints loaded from environment.
  - Optional:
    - Hook points for tracing (e.g., OpenTelemetry) if needed later.

