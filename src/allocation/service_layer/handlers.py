from __future__ import annotations
from allocation.domain import model, events, commands
from allocation.service_layer import unit_of_work
from allocation.adapters import redis_eventpublisher, notifications
from sqlalchemy import text
from dataclasses import asdict
from typing import Callable


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


def add_allocation_to_read_model(
    event: events.Allocated, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        uow.session.execute(
            text(
                """
                INSERT INTO allocations_view (orderid, sku, batchref)
                VALUES (:orderid, :sku, :batchref)
                """
            ),
            dict(orderid=event.orderid, sku=event.sku, batchref=event.batchref),
        )
        uow.commit()


def reallocate(event: events.Deallocated, uow: unit_of_work.AbstractUnitOfWork):
    with uow:
        product = uow.products.get(sku=event.sku)
        product.events.append(commands.Allocate(**asdict(event)))
        uow.commit()


def remove_allocation_from_read_model(
    event: events.Deallocated, uow: unit_of_work.AbstractUnitOfWork
):
    with uow:
        uow.session.execute(
            text(
                """
                DELETE FROM allocations_view
                WHERE orderid = :orderid AND sku = :sku
                """
            ),
            dict(orderid=event.orderid, sku=event.sku),
        )
        uow.commit()


def send_out_of_stock_notification(
    event: events.OutOfStock, notifications: notifications.AbstractNotifications
):
    notifications.send(
        "user@mail.com",
        f"Out of stock for {event.sku}",
    )


def change_batch_quantity(
    command: commands.ChangeBatchQuantity, uow: unit_of_work.SqlAlchemyUnitOfWork
):
    with uow:
        product = uow.products.get_by_batchref(batchref=command.ref)
        product.change_batch_quantity(ref=command.ref, qty=command.qty)
        uow.commit()


def publish_allocated_event(event: events.Allocated, publish: Callable):
    publish("line_allocated", event)


EVENT_HANDLERS = {
    events.OutOfStock: [send_out_of_stock_notification],
    events.Allocated: [
        publish_allocated_event,
        add_allocation_to_read_model,
    ],
    events.Deallocated: [
        remove_allocation_from_read_model,
        reallocate,
    ],
}
COMMAND_HANDLERS = {
    commands.Allocate: allocate,
    commands.CreateBatch: add_batch,
    commands.ChangeBatchQuantity: change_batch_quantity,
}
