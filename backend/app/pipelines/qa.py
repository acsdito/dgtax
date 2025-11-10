from __future__ import annotations

from typing import Any, Dict

from app.config import Settings
from app.repositories.postgres import PostgresRepository
from app.schemas import AnswerResponse, QueryExecution, QueryIntent
from app.services.ollama import OllamaClient
from app.utils.exceptions import LLMResponseFormatError, QueryExecutionError
from app.utils.sql_guard import ensure_safe_query


class QAPipeline:
    """
    Orquestra o fluxo pergunta -> consulta -> formatação da resposta.
    """

    def __init__(
        self,
        ollama_client: OllamaClient,
        repository: PostgresRepository,
        *,
        max_rows: int,
    ) -> None:
        self._ollama = ollama_client
        self._repository = repository
        self._max_rows = max_rows

    @classmethod
    def from_settings(cls, settings: Settings) -> "QAPipeline":
        dsn = (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_database}"
        )

        ollama = OllamaClient(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout=settings.ollama_timeout_seconds,
        )

        repo = PostgresRepository(
            dsn,
            min_size=settings.postgres_min_pool_size,
            max_size=settings.postgres_max_pool_size,
            max_rows=settings.max_rows,
        )

        return cls(ollama, repo, max_rows=settings.max_rows)

    async def start(self) -> None:
        await self._ollama.start()
        await self._repository.start()

    async def stop(self) -> None:
        await self._ollama.close()
        await self._repository.close()

    async def run(self, pergunta: str) -> AnswerResponse:
        avisos: list[str] = []
        intent = await self._ollama.plan_query(pergunta, self._max_rows)
        intent = self._sanitize_intent(intent, avisos)
        query_execution = await self._execute_intent(intent, avisos)
        resposta = await self._ollama.compose_answer(pergunta, query_execution, avisos)

        return AnswerResponse(
            pergunta_original=pergunta,
            resposta_modelada=resposta,
            resumo_consulta=query_execution,
            avisos=avisos,
        )

    def _sanitize_intent(self, intent: QueryIntent, avisos: list[str]) -> QueryIntent:
        if not intent.sql.strip():
            raise LLMResponseFormatError("A IA não conseguiu gerar uma consulta SQL para a pergunta informada.")

        ensure_safe_query(intent.sql)

        if "limit" not in intent.sql.lower():
            intent.sql = f"{intent.sql.rstrip()} LIMIT {self._max_rows}"
            avisos.append(f"Limite padrão de {self._max_rows} linhas aplicado automaticamente.")

        return intent

    async def _execute_intent(self, intent: QueryIntent, avisos: list[str]) -> QueryExecution:
        try:
            rows, limit_applied = await self._repository.fetch(intent.sql, intent.parametros)
        except QueryExecutionError:
            raise

        data = list(rows)
        if limit_applied:
            avisos.append(
                "A consulta retornou mais linhas do que o limite configurado. Apenas as primeiras foram consideradas."
            )

        return QueryExecution(
            sql=intent.sql,
            parametros=_stringify_params(intent.parametros),
            linhas=data,
            total_linhas=len(data),
            limite_aplicado=limit_applied,
        )


def _stringify_params(params: Dict[str, Any]) -> Dict[str, Any]:
    return {k: v for k, v in params.items()}
