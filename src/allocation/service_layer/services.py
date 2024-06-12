from allocation.adapters.repository import AbstractRepository
from allocation.domain import model
from datetime import date
from typing import Optional


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
    ref: str, sku: str, qty: int, eta: Optional[date], repo: AbstractRepository, session
):
    batch = model.Batch(ref, sku, qty, eta)
    repo.add(batch)
    session.commit()


def allocate(
    orderid: str,
    sku: str,
    qty: int,
    repo: AbstractRepository,
    session,
) -> str:
    batches = repo.list()
    line = model.OrderLine(orderid, sku, qty)

    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku: {line.sku}")

    batchref = model.allocate(line, batches)
    session.commit()

    return batchref


def deallocate(orderid: str, sku: str, qty: int, repo: AbstractRepository, session):
    batches = repo.list()
    line = model.OrderLine(orderid, sku, qty)

    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku: {line.sku}")

    try:
        batch = next(batch for batch in batches if batch.sku == line.sku)
    except StopIteration:
        return

    batch.deallocate(line)
    session.commit()
