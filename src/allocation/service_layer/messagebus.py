from __future__ import annotations
import logging
from allocation.domain import events, commands
from allocation.service_layer import handlers
from typing import Union, List, TYPE_CHECKING


if TYPE_CHECKING:
    from allocation.service_layer import unit_of_work


logger = logging.getLogger(__name__)

EVENT_HANDLERS = {
    events.OutOfStock: [handlers.send_out_of_stock_notification],
    events.Allocated: [handlers.publish_allocated_event],
}
COMMAND_HANDLERS = {
    commands.Allocate: handlers.allocate,
    commands.CreateBatch: handlers.add_batch,
    commands.ChangeBatchQuantity: handlers.change_batch_quantity,
}

Message = Union[commands.Command, events.Event]


def handle(message: Message, uow: unit_of_work.AbstractUnitOfWork):
    results = []
    queue = [message]
    while queue:
        message = queue.pop(0)
        if isinstance(message, events.Event):
            handle_event(message, queue, uow)
        elif isinstance(message, commands.Command):
            cmd_result = handle_command(message, queue, uow)
            results.append(cmd_result)
        else:
            raise Exception(f"{message} was not an Event or Command")

    return results


def handle_event(
    event: events.Event, queue: List[Message], uow: unit_of_work.AbstractUnitOfWork
):
    for handler in EVENT_HANDLERS[type(event)]:
        try:
            logger.debug(f"handling event {event} with handler {handler}")
            handler(event, uow=uow)
            queue.extend(uow.collect_new_events())
        except Exception:
            logger.exception(f"Exception handling event {event}")
            continue


def handle_command(
    command: commands.Command,
    queue: List[Message],
    uow: unit_of_work.AbstractUnitOfWork,
):
    logger.debug(f"handling command {command}")
    try:
        handler = COMMAND_HANDLERS[type(command)]
        result = handler(command, uow)
        queue.extend(uow.collect_new_events())
        return result
    except Exception:
        logger.exception(f"Exception handling command {command}")
        raise
