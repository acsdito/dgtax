from fastapi import Depends, FastAPI, HTTPException, status

from app.config import get_settings
from app.pipelines.qa import QAPipeline
from app.schemas import AnswerResponse, QuestionRequest
from app.utils.exceptions import (
    LLMResponseFormatError,
    QueryExecutionError,
    QueryValidationError,
)

settings = get_settings()
app = FastAPI(title=settings.api_title, version=settings.api_version)


async def get_pipeline() -> QAPipeline:
    pipeline: QAPipeline = app.state.qa_pipeline
    return pipeline


@app.on_event("startup")
async def _startup() -> None:
    pipeline = QAPipeline.from_settings(settings)
    await pipeline.start()
    app.state.qa_pipeline = pipeline


@app.on_event("shutdown")
async def _shutdown() -> None:
    pipeline: QAPipeline = app.state.qa_pipeline
    await pipeline.stop()


@app.post(
    "/perguntas",
    response_model=AnswerResponse,
    status_code=status.HTTP_200_OK,
    summary="Processa perguntas sobre benefícios fiscais",
)
async def perguntar(payload: QuestionRequest, pipeline: QAPipeline = Depends(get_pipeline)) -> AnswerResponse:
    try:
        return await pipeline.run(payload.pergunta)
    except QueryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except QueryExecutionError as exc:
        raise HTTPException(status_code=422, detail=f"Falha ao executar consulta: {exc}") from exc
    except LLMResponseFormatError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
