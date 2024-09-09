import json
import logging
import redis

from allocation import config, bootstrap
from allocation.adapters import orm
from allocation.domain import commands
from allocation.service_layer import unit_of_work, messagebus


r = redis.Redis(**config.get_redis_host_and_port())


def main():
    bus = bootstrap.bootstrap()
    pubsub = r.pubsub(ignore_subscribe_messages=True)
    pubsub.subscribe("change_batch_quantity")

    for m in pubsub.listen():
        handle_change_batch_quantity(m, bus)


def handle_change_batch_quantity(m, bus):
    logging.debug(f"handling {m}")
    data = json.loads(m["data"])
    cmd = commands.ChangeBatchQuantity(ref=data["batchref"], qty=data["qty"])
    bus.handle(cmd)


if __name__ == "__main__":
    main()
