from __future__ import annotations

import json
from typing import Any, Dict, Optional

import httpx

from app.llm.prompts import ANSWER_COMPOSER_SYSTEM_PROMPT, SQL_PLANNER_SYSTEM_PROMPT
from app.schemas import QueryIntent, QueryExecution
from app.utils.exceptions import LLMResponseFormatError


class OllamaClient:
    """
    Cliente assíncrono para comunicação com o servidor Ollama.
    """

    def __init__(self, base_url: str, model: str, timeout: int = 120) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self._base_url, timeout=self._timeout)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("OllamaClient não foi inicializado. Execute start() durante o startup da aplicação.")
        return self._client

    async def chat(self, messages: list[dict[str, str]], *, json_mode: bool = False) -> str:
        client = await self._ensure_client()
        payload: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "stream": False,
        }

        if json_mode:
            payload["format"] = "json"

        response = await client.post("/api/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        return data["message"]["content"]

    async def plan_query(self, pergunta: str, limite_padrao: int) -> QueryIntent:
        system_prompt = SQL_PLANNER_SYSTEM_PROMPT.replace("%(limite_padrao)s", str(limite_padrao))
        content = await self.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": pergunta},
            ],
            json_mode=True,
        )

        try:
            payload: Dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMResponseFormatError("Resposta da IA (planejamento) não é um JSON válido.") from exc

        return QueryIntent(
            sql=payload.get("sql") or "",
            parametros=payload.get("parametros") or {},
            justificativa=payload.get("justificativa"),
            confianca=payload.get("confianca"),
        )

    async def compose_answer(
        self,
        pergunta: str,
        consulta: QueryExecution,
        avisos: list[str],
    ) -> str:
        context_json = json.dumps(
            {
                "pergunta": pergunta,
                "consulta": consulta.model_dump(),
                "avisos": avisos,
            },
            ensure_ascii=False,
        )

        content = await self.chat(
            [
                {"role": "system", "content": ANSWER_COMPOSER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Contexto estruturado:\n{context_json}"},
            ]
        )

        return content.strip()
