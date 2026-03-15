from __future__ import annotations

import logging
import uuid
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.graph.graph_builder import get_compiled_graph
from app.logging_config import setup_logging
from app.schemas import ChatResponse, UserQuery

logger = logging.getLogger(__name__)

# Import primer3 app to mount on same server (optional)
try:
    from primer3_service.main import app as primer3_app
    PRIMER3_APP_AVAILABLE = True
except ImportError:
    primer3_app = None
    PRIMER3_APP_AVAILABLE = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info("Starting mutation research chat agent")
    get_compiled_graph()
    yield
    logger.info("Shutting down")


app = FastAPI(
    title="Mutation Research Chat Agent",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount primer design on same server at /primer3 (so one process serves both)
if PRIMER3_APP_AVAILABLE:
    app.mount("/primer3", primer3_app)
    logger.info("Primer3 design service mounted at /primer3")


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(query: UserQuery) -> ChatResponse:
    trace_id = uuid.uuid4().hex[:12]
    logger.info("[%s] Received query: %s", trace_id, query.query_text[:80])

    max_iter = query.max_iterations or settings.default_max_iterations

    initial_state = {
        "user_query": query,
        "search_results": [],
        "hypotheses": [],
        "judge_decision": None,
        "iterations": 0,
        "max_iterations": max_iter,
        "chat_response": None,
    }

    graph = get_compiled_graph()

    try:
        final_state = await graph.ainvoke(initial_state)
    except Exception:
        logger.exception("[%s] Graph execution failed", trace_id)
        raise HTTPException(status_code=500, detail="Internal agent error")

    chat_response: ChatResponse | None = final_state.get("chat_response")
    if chat_response is None:
        raise HTTPException(status_code=500, detail="No response was produced by the agent")

    logger.info("[%s] Response generated (iterations=%d)", trace_id, chat_response.iterations_used)
    return chat_response


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/v1/design-from-alignment")
async def proxy_design_from_alignment(request: Request):
    """
    Primer design (design-from-alignment). When primer3 is mounted on this server,
    calls it in-process; otherwise proxies to APP_PRIMER3_BASE_URL.
    """
    try:
        body = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {e}") from e

    # Same server: call primer design in-process (primer3 is mounted at /primer3)
    if PRIMER3_APP_AVAILABLE:
        from primer3_service.design import run_design_from_alignment, to_simplified_response
        from primer3_service.schemas import AlignmentRequest
        try:
            req = AlignmentRequest.model_validate(body)
            full = run_design_from_alignment(req)
            simplified = to_simplified_response(full)
            return simplified.model_dump()
        except Exception as e:
            logger.exception("Design-from-alignment failed")
            raise HTTPException(status_code=422, detail=str(e)) from e

    # Separate server: proxy to primer3 service
    if not settings.primer3_base_url:
        raise HTTPException(
            status_code=503,
            detail="Primer3 not available (mount primer3_service or set APP_PRIMER3_BASE_URL)",
        )
    url = f"{settings.primer3_base_url.rstrip('/')}/design-from-alignment"
    logger.info("Proxy POST %s (body keys: %s)", url, list(body.keys()) if isinstance(body, dict) else "non-dict")
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(url, json=body)
        except httpx.ConnectError as e:
            logger.warning("Primer3 service unreachable at %s: %s", url, e)
            raise HTTPException(
                status_code=503,
                detail=f"Primer3 unreachable at {settings.primer3_base_url}. Run it or mount at /primer3.",
            ) from e
        except Exception as e:
            logger.exception("Primer3 proxy request failed")
            raise HTTPException(status_code=502, detail=str(e)) from e
    if r.status_code >= 400:
        logger.warning("Primer3 returned %s: %s", r.status_code, r.text[:500])
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()
