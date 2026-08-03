"""FastAPI service.

Thin. All behavior lives in the graph, which is what makes the graph testable
without HTTP and the API replaceable without touching logic.
"""

from __future__ import annotations

from deduction_graph import SUPPORTED_TAX_YEARS, __version__
from deduction_graph.api.schemas import (
    AskRequest,
    AskResponse,
    HealthResponse,
    TrailStep,
)
from deduction_graph.config import settings
from deduction_graph.graph.build import run_sequential
from deduction_graph.graph.nodes.retrieve import get_retriever, set_retriever
from deduction_graph.graph.state import GraphState
from deduction_graph.observability.trace import configure_logging
from deduction_graph.retrieval.hybrid import HybridRetriever
from deduction_graph.retrieval.store import InMemoryStore
from deduction_graph.tools.registry import tool_schemas

try:
    from fastapi import FastAPI, HTTPException
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "fastapi is not installed. Install with `pip install -e '.[api]'`."
    ) from exc

app = FastAPI(
    title="deduction-graph",
    version=__version__,
    description=(
        "An auditable agentic assistant for U.S. federal income tax deduction "
        "questions. A software engineering demonstration, not tax advice."
    ),
)


@app.on_event("startup")
def _startup() -> None:
    configure_logging()
    # TODO(milestone-2): load the committed corpus and, when configured, the
    # Chroma dense index. Fixture corpus keeps the service runnable meanwhile.
    from evals.datasets.fixture_corpus import FIXTURE_CHUNKS

    store = InMemoryStore()
    store.add(list(FIXTURE_CHUNKS))
    set_retriever(HybridRetriever(sparse=store))


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        version=__version__,
        supported_tax_years=list(SUPPORTED_TAX_YEARS),
        llm_configured=settings().llm_enabled,
        corpus_chunks=get_retriever().sparse.count(),
    )


@app.get("/tools")
def tools() -> list[dict]:
    """Tool discovery. Every deterministic calculation the system can perform."""
    return tool_schemas()


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    if request.profile and request.profile.tax_year not in SUPPORTED_TAX_YEARS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"tax_year {request.profile.tax_year} is not supported. "
                f"Supported: {list(SUPPORTED_TAX_YEARS)}. This service will not "
                "answer from an adjacent year."
            ),
        )

    state = run_sequential(
        GraphState(
            question=request.question,
            profile=request.profile,
            conversation=request.conversation,
        )
    )

    return AskResponse(
        outcome=state.outcome.value,
        answer=state.final_answer,
        tax_year=state.scope.tax_year,
        provisions=[p.value for p in state.scope.provisions],
        computation_trail=[
            TrailStep(
                label=s.label,
                detail=s.detail,
                amount=str(s.value.amount) if s.value is not None else None,
                rule_source=s.rule_source,
            )
            for s in state.computation_trail
        ],
        citations=list(state.citations),
        unverified_parameters=list(state.unverified_parameters),
        warnings=list(state.warnings),
        escalation_reason=state.escalation_reason,
    )
