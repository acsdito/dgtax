from __future__ import annotations

import re
from typing import Iterable, List, Set

import sqlparse
from sqlparse.sql import Identifier, IdentifierList
from sqlparse.tokens import Keyword, DML, Whitespace, Wildcard

from .exceptions import QueryValidationError

_FORBIDDEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r";\s*$", flags=re.IGNORECASE),
    re.compile(r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke)\b", flags=re.IGNORECASE),
    re.compile(r"\b(pg_|information_schema|pg_catalog)\b", flags=re.IGNORECASE),
)

_ALLOWED_TABLES: Set[str] = {
    "empresa",
    "beneficio_empresa",
    "beneficios",
    "empresa_atividade",
    "empresa_socio",
}


def ensure_safe_query(sql: str) -> None:
    """
    Garante que a consulta SQL seja somente leitura e esteja limitada ao escopo permitido.
    """

    normalized = sql.strip()
    if not normalized:
        raise QueryValidationError("Consulta vazia recebida da IA.")

    # Divide instruções por ';' e garante apenas uma consulta.
    statements = [stmt for stmt in sqlparse.split(normalized) if stmt.strip()]
    if len(statements) != 1:
        raise QueryValidationError("Somente uma instrução SELECT/WITH é permitida por consulta.")

    parsed = sqlparse.parse(statements[0])
    if not parsed:
        raise QueryValidationError("Não foi possível analisar a consulta SQL gerada.")

    statement = parsed[0]
    first_token = _first_meaningful_token(statement)
    if first_token is None or first_token.value.upper() not in {"SELECT", "WITH"}:
        raise QueryValidationError("Somente instruções SELECT ou WITH são permitidas.")

    for pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(normalized):
            raise QueryValidationError("A consulta gerada contém comandos não permitidos ou múltiplas instruções.")

    tables = _extract_referenced_tables(statement)
    disallowed_tables = tables - _ALLOWED_TABLES
    if disallowed_tables:
        raise QueryValidationError(f"Tabelas não permitidas identificadas na consulta: {sorted(disallowed_tables)}")

    columns = _extract_select_columns(statement)
    ensure_allowed_columns(columns)


def ensure_allowed_columns(columns: Iterable[str]) -> None:
    """
    Garante que todas as colunas solicitadas possuam nomes válidos (sem caracteres suspeitos).
    """

    invalid: List[str] = []
    for col in columns:
        cleaned = col.strip()
        if not cleaned:
            continue

        if cleaned == "*" or re.fullmatch(r"[a-zA-Z0-9_\.]+?\.\*", cleaned):
            # Permite wildcard simples (SELECT * ou tabela.*).
            continue

        if not re.fullmatch(r"[a-zA-Z0-9_\.\s\"%'(),:\-><=+/*%]+", cleaned):
            invalid.append(col)

    if invalid:
        raise QueryValidationError(f"Colunas inválidas detectadas na consulta: {invalid}")


def _first_meaningful_token(statement: sqlparse.sql.Statement):
    for token in statement.tokens:
        if token.ttype not in (Whitespace,):
            if token.is_group:
                return _first_meaningful_token(token)
            return token
    return None


def _extract_referenced_tables(statement: sqlparse.sql.Statement) -> Set[str]:
    tables: Set[str] = set()

    def _process_identifier(identifier: Identifier) -> None:
        # Aceita apenas schemaless ou schema public.
        parent = identifier.get_parent_name()
        if parent and parent.lower() != "public":
            raise QueryValidationError("Acesso a schemas externos não é permitido.")

        real_name = identifier.get_real_name() or identifier.get_name()
        if real_name:
            tables.add(real_name.lower())

    expecting_table = False

    for token in statement.tokens:
        if token.is_group:
            tables.update(_extract_referenced_tables(token))
            continue

        if token.ttype is Keyword:
            keyword = token.value.upper()
            if keyword == "FROM" or keyword.endswith("JOIN"):
                expecting_table = True
            else:
                expecting_table = False
            continue

        if expecting_table:
            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    _process_identifier(identifier)
                expecting_table = False
            elif isinstance(token, Identifier):
                _process_identifier(token)
                expecting_table = False
            elif token.ttype in (Whitespace,):
                continue
            else:
                expecting_table = False
            continue

    return tables


def _extract_select_columns(statement: sqlparse.sql.Statement) -> List[str]:
    columns: List[str] = []
    select_seen = False

    for token in statement.tokens:
        if token.ttype is DML and token.value.upper() == "SELECT":
            select_seen = True
            continue

        if select_seen:
            if token.ttype is Keyword and token.value.upper() == "FROM":
                break

            if isinstance(token, IdentifierList):
                for identifier in token.get_identifiers():
                    columns.append(identifier.value)
            elif isinstance(token, Identifier):
                columns.append(token.value)
            elif token.ttype in (Whitespace,):
                continue
            elif token.ttype is Wildcard:
                columns.append(token.value)
            elif token.is_group:
                columns.extend(_extract_select_columns(token))

    return columns
