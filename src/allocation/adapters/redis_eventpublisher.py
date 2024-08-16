import json
import logging
import redis
from dataclasses import asdict

from allocation import config
from allocation.domain import events


r = redis.Redis(**config.get_redis_host_and_port())


def publish(channel, event: events.Event):
    logging.debug(f"Publishing channel={channel}, event={event}")
    r.publish(channel, json.dumps(asdict(event)))
