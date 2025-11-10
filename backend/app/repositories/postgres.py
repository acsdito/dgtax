from __future__ import annotations

from typing import Any, Dict, Iterable, Tuple

from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.utils.exceptions import QueryExecutionError


class PostgresRepository:
    """
    Responsável por executar consultas seguras no banco PostgreSQL com pool de conexões.
    """

    def __init__(
        self,
        dsn: str,
        *,
        min_size: int = 1,
        max_size: int = 5,
        max_rows: int = 200,
    ) -> None:
        self._dsn = dsn
        self._pool = AsyncConnectionPool(
            conninfo=dsn,
            min_size=min_size,
            max_size=max_size,
            timeout=10,
        )
        self._max_rows = max_rows

    async def start(self) -> None:
        await self._pool.open(wait=True)

    async def close(self) -> None:
        await self._pool.close()

    async def fetch(self, sql: str, params: Dict[str, Any]) -> Tuple[Iterable[Dict[str, Any]], bool]:
        try:
            async with self._pool.connection() as conn:  # type: AsyncConnection[Any]
                async with conn.cursor(row_factory=dict_row) as cur:
                    await cur.execute(sql, params)
                    rows = await cur.fetchmany(self._max_rows + 1)
        except Exception as exc:  # noqa: BLE001
            raise QueryExecutionError(str(exc)) from exc

        limit_applied = len(rows) > self._max_rows
        return rows[: self._max_rows], limit_applied
