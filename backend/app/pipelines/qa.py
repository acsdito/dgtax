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

    def _detectar_setor(self, pergunta: str) -> tuple[bool, str]:
        """
        Detecta se a pergunta menciona um tipo/setor de empresa.
        Retorna (tem_setor, palavra_chave)
        """
        setores_map = {
            "construtora": "construcao",
            "construcao": "construcao",
            "construção": "construcao",
            "banco": "ultipl",  # Filtra "Bancos múltiplos/multiplos", evita "fabricação de bancos"
            "bancos": "ultipl",
            "financeira": "financeiro",
            "industria": "industria",
            "fabrica": "fabrica",
            "hospital": "hospital",
            "clinica": "saude",
            "hotel": "hotel",
            "restaurante": "restaurante",
            "comercio": "comercio",
            "varejo": "varejo",
            "loja": "loja",
            "tecnologia": "tecnologia",
            "software": "software",
            "farmacia": "farmacia",
            "escola": "educacao",
            "transporte": "transporte"
        }
        
        pergunta_lower = pergunta.lower()
        for palavra, chave in setores_map.items():
            if palavra in pergunta_lower:
                return True, chave
        
        return False, ""

    async def run(self, pergunta: str, max_retries: int = 3) -> AnswerResponse:
        avisos: list[str] = []
        
        # Detecta se há filtro de setor na pergunta
        tem_setor, palavra_setor = self._detectar_setor(pergunta)
        if tem_setor:
            pergunta_enriquecida = f"{pergunta} [IMPORTANTE: Filtrar por CNAE com descricao_cnae ILIKE '%{palavra_setor}%']"
        else:
            pergunta_enriquecida = pergunta
        
        # Limpa histórico de erros anteriores (nova pergunta)
        self._ollama._clear_error_history()
        
        # Tentativas com retry automático em caso de erro SQL
        for attempt in range(max_retries):
            try:
                intent = await self._ollama.plan_query(pergunta_enriquecida, self._max_rows, attempt)
                intent = self._sanitize_intent(intent, avisos)
                query_execution = await self._execute_intent(intent, avisos)
                
                # Sucesso - limpa histórico de erros e sai do loop
                self._ollama._clear_error_history()
                if attempt > 0:
                    avisos.append(f"Consulta corrigida automaticamente após {attempt} tentativa(s).")
                break
                
            except QueryExecutionError as e:
                if attempt < max_retries - 1:
                    # Ainda há tentativas restantes - envia erro para IA corrigir
                    print(f"❌ Tentativa {attempt + 1}/{max_retries} falhou: {e}")
                    await self._ollama.register_error(str(e))
                    continue
                else:
                    # Última tentativa falhou - limpa histórico e propaga erro ao usuário
                    self._ollama._clear_error_history()
                    raise
            except (LLMResponseFormatError, Exception) as e:
                # Erros não relacionados a SQL - limpa histórico e propaga imediatamente
                self._ollama._clear_error_history()
                raise
        
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

        # Remove parâmetros vazios ou nulos (ex: {"uf": ""} ou {"uf": null})
        if intent.parametros:
            intent.parametros = {
                k: v for k, v in intent.parametros.items() 
                if v not in ("", None, "null", "NULL")
            }

        if "limit" not in intent.sql.lower():
            intent.sql = f"{intent.sql.rstrip()} LIMIT {self._max_rows}"
            avisos.append(f"Limite padrão de {self._max_rows} linhas aplicado automaticamente.")

        return intent

    async def _execute_intent(self, intent: QueryIntent, avisos: list[str]) -> QueryExecution:
        try:
            print("Consulta gerada pela IA:", intent.sql)
            print("Parâmetros da consulta:", intent.parametros)
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
