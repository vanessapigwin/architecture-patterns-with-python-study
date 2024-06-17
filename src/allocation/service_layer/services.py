from allocation.domain import model
from allocation.service_layer import unit_of_work
from datetime import date
from typing import Optional


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
    ref: str,
    sku: str,
    qty: int,
    eta: Optional[date],
    uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get(sku=sku)
        if product is None:
            product = model.Product(sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(ref, sku, qty, eta))
        uow.commit()


def allocate(
    orderid: str, sku: str, qty: int, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = model.OrderLine(orderid, sku, qty)

    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku: {line.sku}")
        batchref = product.allocate(line)
        uow.commit()

    return batchref


def deallocate(
    batchref: str,
    orderid: str,
    sku: str,
    qty: int,
    uow: unit_of_work.AbstractUnitOfWork,
):
    line = model.OrderLine(orderid, sku, qty)

    with uow:
        product = uow.products.get(sku=line.sku)
        if product is None:
            raise InvalidSku(f"Invalid sku: {line.sku}")

        try:
            batch = next(b for b in product.batches if b.reference == batchref)
            batch.deallocate(line)
        except StopIteration:
            raise InvalidSku(f"Invalid sku: {line.sku}")

        uow.commit()
