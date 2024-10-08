from __future__ import annotations
import logging
from allocation.domain import events, commands
from allocation.service_layer import handlers
from typing import Union, List, TYPE_CHECKING, Dict, Type, Callable


if TYPE_CHECKING:
    from allocation.service_layer import unit_of_work


logger = logging.getLogger(__name__)

Message = Union[commands.Command, events.Event]


class MessageBus:

    def __init__(
        self,
        uow: unit_of_work.AbstractUnitOfWork,
        event_handlers: Dict[Type[events.Event], List[Callable]],
        command_handlers: Dict[Type[commands.Command], List[Callable]],
    ):
        self.uow = uow
        self.event_handlers = event_handlers
        self.command_handlers = command_handlers

    def handle(self, message: Message):
        results = []
        self.queue = [message]
        while self.queue:
            message = self.queue.pop(0)
            if isinstance(message, events.Event):
                self.handle_event(message)
            elif isinstance(message, commands.Command):
                self.handle_command(message)
            else:
                raise Exception(f"{message} was not an Event or Command")

        return results

    def handle_event(self, event: events.Event):
        for handler in self.event_handlers[type(event)]:
            try:
                logger.debug(f"handling event {event} with handler {handler}")
                handler(event)
                self.queue.extend(self.uow.collect_new_events())
            except Exception:
                logger.exception(f"Exception handling event {event}")
                continue

    def handle_command(self, command: commands.Command):
        logger.debug(f"handling command {command}")
        try:
            handler = self.command_handlers[type(command)]
            handler(command)
            self.queue.extend(self.uow.collect_new_events())
        except Exception:
            logger.exception(f"Exception handling command {command}")
            raise
