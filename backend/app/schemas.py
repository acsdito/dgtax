from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class QuestionRequest(BaseModel):
    pergunta: str = Field(..., description="Pergunta em linguagem natural feita pelo usuário final.")
    contexto: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadados opcionais para enriquecer a pergunta (por exemplo, usuário, canal, filtros pré-definidos).",
    )


class QueryIntent(BaseModel):
    sql: str = Field(..., description="Consulta SQL gerada pela IA. Deve ser somente leitura.")
    parametros: Dict[str, Any] = Field(
        default_factory=dict,
        description="Parâmetros nomeados utilizados na consulta. O driver fará o binding seguro.",
    )
    justificativa: Optional[str] = Field(default=None, description="Raciocínio resumido sobre o porquê da consulta.")
    confianca: Optional[float] = Field(default=None, description="Confiança estimada da IA (0 a 1).")


class QueryExecution(BaseModel):
    sql: str
    parametros: Dict[str, Any]
    linhas: List[Dict[str, Any]]
    total_linhas: int
    limite_aplicado: bool


class AnswerResponse(BaseModel):
    pergunta_original: str
    resposta_modelada: str
    resumo_consulta: QueryExecution
    avisos: List[str] = Field(default_factory=list)
