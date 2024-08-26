from __future__ import annotations
from allocation.service_layer import unit_of_work
from sqlalchemy import text


def allocations(orderid: str, uow: unit_of_work.AbstractUnitOfWork):
    with uow:
        results = list(
            uow.session.execute(
                text(
                    """
                    SELECT sku, batchref FROM allocations_view
                    WHERE orderid = :orderid
                    """
                ),
                dict(orderid=orderid),
            )
        )
    return [{"sku": sku, "batchref": batchref} for sku, batchref in results]
