from allocation.adapters.repository import AbstractRepository
from allocation.domain import model


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(batch: model.Batch, repo: AbstractRepository, session):
    repo.add(batch)
    session.commit()


def allocate(line: model.OrderLine, repo: AbstractRepository, session) -> str:
    batches = repo.list()

    if not is_valid_sku(line.sku, batches):
        raise InvalidSku(f"Invalid sku: {line.sku}")

    batchref = model.allocate(line, batches)
    session.commit()

    return batchref


def deallocate(line: model.OrderLine, repo: AbstractRepository, session):
    pass
