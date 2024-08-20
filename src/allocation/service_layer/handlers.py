from __future__ import annotations
from allocation.domain import model, events, commands
from allocation.service_layer import unit_of_work
from allocation.adapters import redis_eventpublisher


class InvalidSku(Exception):
    pass


def is_valid_sku(sku, batches):
    return sku in {b.sku for b in batches}


def add_batch(
    command: commands.CreateBatch,
    uow: unit_of_work.AbstractUnitOfWork,
):
    with uow:
        product = uow.products.get(sku=command.sku)
        if product is None:
            product = model.Product(command.sku, batches=[])
            uow.products.add(product)
        product.batches.append(
            model.Batch(command.ref, command.sku, command.qty, command.eta)
        )
        uow.commit()


def allocate(command: commands.Allocate, uow: unit_of_work.AbstractUnitOfWork) -> str:
    line = model.OrderLine(command.orderid, command.sku, command.qty)

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


def change_batch_quantity(
    command: commands.ChangeBatchQuantity, uow: unit_of_work.SqlAlchemyUnitOfWork
):
    with uow:
        product = uow.products.get_by_batchref(batchref=command.ref)
        product.change_batch_quantity(ref=command.ref, qty=command.qty)
        uow.commit()


def publish_allocated_event(
    event: events.Allocated, uow: unit_of_work.AbstractUnitOfWork
):
    redis_eventpublisher.publish("line_allocated", event)
