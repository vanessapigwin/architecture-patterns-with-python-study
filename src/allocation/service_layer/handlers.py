from __future__ import annotations
from allocation.domain import model, events
from allocation.service_layer import unit_of_work
from datetime import date
from typing import Optional


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
    event: events.BatchCreated,
    uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get(sku=event.sku)
        if product is None:
            product = model.Product(event.sku, batches=[])
            uow.products.add(product)
        product.batches.append(model.Batch(event.ref, event.sku, event.qty, event.eta))
        uow.commit()


def allocate(
    event: events.AllocationRequired, uow: unit_of_work.AbstractUnitOfWork
) -> str:
    line = model.OrderLine(event.orderid, event.sku, event.qty)

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


def send_out_of_stock_notification(
    event: events.OutOfStock, uow: unit_of_work.AbstractUnitOfWork
):
    print(event.sku)
