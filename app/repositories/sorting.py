from typing import Any
from sqlalchemy.sql import Select

from app.enums import SortDirection


def sort_data(
    statement: Select[Any],
    *,
    sort_column: Any,
    direction: SortDirection,
    tie_breaker: Any | None = None,
) -> Select[Any]:
    order = "desc" if direction == SortDirection.DESC else "asc"

    order_expression = getattr(sort_column, order)().nulls_last()
    statement = statement.order_by(order_expression)

    if tie_breaker is not None and sort_column is not tie_breaker:
        statement = statement.order_by(getattr(tie_breaker, order)())

    return statement
