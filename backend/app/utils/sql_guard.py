from __future__ import annotations

import re
from typing import Iterable

from .exceptions import QueryValidationError

_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r";\s*$", flags=re.IGNORECASE),
    re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke)\b", flags=re.IGNORECASE),
    re.compile(r"\b(pg_|information_schema|pg_catalog)\b", flags=re.IGNORECASE),
)


def ensure_safe_query(sql: str) -> None:
    """
    Garante que a consulta SQL seja somente leitura e esteja limitada ao escopo permitido.
    """

    normalized = sql.strip()
    if not normalized:
        raise QueryValidationError("Consulta vazia recebida da IA.")

    first_keyword = normalized.split(maxsplit=1)[0].lower()
    if first_keyword not in {"select", "with"}:
        raise QueryValidationError("Somente instruções SELECT/WITH são permitidas.")

    for pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(normalized):
            raise QueryValidationError("A consulta gerada contém comandos não permitidos ou múltiplas instruções.")


def ensure_allowed_columns(columns: Iterable[str]) -> None:
    """
    Garante que todas as colunas solicitadas possuam nomes válidos (sem caracteres suspeitos).
    """

    invalid = [col for col in columns if not re.fullmatch(r"[a-zA-Z0-9_\.->\s]+", col)]
    if invalid:
        raise QueryValidationError(f"Colunas inválidas detectadas na consulta: {invalid}")
