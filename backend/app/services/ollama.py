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
        self._error_history: list[str] = []  # Histórico de erros para retry

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

    async def register_error(self, error_message: str) -> None:
        """Registra um erro de execução SQL para feedback na próxima tentativa."""
        self._error_history.append(error_message)

    def _clear_error_history(self) -> None:
        """Limpa o histórico de erros (chamado após sucesso)."""
        self._error_history.clear()

    def _clean_malformed_json(self, content: str) -> str:
        """
        Limpa JSON malformado removendo quebras de linha excessivas e espaços dentro de strings.
        Tenta corrigir problemas comuns de formatação da IA.
        """
        import re
        
        # Remove múltiplas quebras de linha consecutivas dentro de strings JSON
        # Padrão: "sql": "WITH cte AS (\n\n\n..." -> "sql": "WITH cte AS (..."
        content = re.sub(r'\\n\s*\\n+', r' ', content)
        
        # Remove tabs e espaços excessivos dentro de strings SQL
        content = re.sub(r'\\t+', r' ', content)
        content = re.sub(r'\s{2,}', r' ', content)
        
        return content.strip()

    async def plan_query(self, pergunta: str, limite_padrao: int, attempt: int = 0) -> QueryIntent:
        system_prompt = SQL_PLANNER_SYSTEM_PROMPT.replace("%(limite_padrao)s", str(limite_padrao))
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Se houver erros anteriores, adiciona contexto de correção
        if self._error_history:
            error_context = "\n\n".join([
                f"ERRO NA TENTATIVA ANTERIOR {i+1}: {err}" 
                for i, err in enumerate(self._error_history)
            ])
            user_message = (
                f"ATENÇÃO: As tentativas anteriores geraram erros SQL. Corrija os problemas identificados.\n\n"
                f"{error_context}\n\n"
                f"Analise os erros acima e gere uma consulta SQL CORRIGIDA para a pergunta:\n"
                f"{pergunta}\n\n"
                "Retorne EXATAMENTE um objeto JSON seguindo o formato especificado. "
                "Não adicione texto extra, nem comentários, nem blocos de código."
            )
        else:
            user_message = (
                "Retorne EXATAMENTE um objeto JSON seguindo o formato especificado. "
                "Não adicione texto extra, nem comentários, nem blocos de código. "
                "Pergunta do usuário:\n"
                f"{pergunta}"
            )
        
        messages.append({"role": "user", "content": user_message})
        
        content = await self.chat(messages, json_mode=True)

        # Limpa JSON malformado (remove quebras de linha excessivas dentro de strings)
        content = self._clean_malformed_json(content)

        try:
            payload: Dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as exc:
            # Se ainda falhar após limpeza, tenta novamente com feedback
            if attempt < 2:  # Máximo 2 tentativas de limpeza
                await self.register_error(
                    f"JSON malformado retornado. Erro: {str(exc)}. "
                    "IMPORTANTE: Retorne JSON valido em UMA UNICA LINHA, sem quebras de linha dentro do SQL."
                )
                return await self.plan_query(pergunta, limite_padrao, attempt + 1)
            
            raise LLMResponseFormatError(
                f"Resposta da IA (planejamento) não é um JSON válido. Conteúdo truncado: {content[:200]!r}"
            ) from exc

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
            default=str,
        )

        content = await self.chat(
            [
                {"role": "system", "content": ANSWER_COMPOSER_SYSTEM_PROMPT},
                {"role": "user", "content": f"Contexto estruturado:\n{context_json}"},
            ]
        )

        return content.strip()
