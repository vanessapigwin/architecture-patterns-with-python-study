import api_client
import pytest
import redis_client
import json
from tenacity import Retrying, stop_after_delay
from conftest import random_batchref, random_orderid, random_sku


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
@pytest.mark.usefixtures("restart_redis_pubsub")
def test_change_batch_quantity_leading_to_reallocation():
    orderid, sku = random_orderid(), random_sku()
    earlier_batch, later_batch = random_batchref("old"), random_batchref("newer")
    api_client.post_to_add_batch(earlier_batch, sku, 10, eta="2022-01-01")
    api_client.post_to_add_batch(later_batch, sku, 10, eta="2022-01-02")
    response = api_client.post_to_allocate(orderid, sku, 10)
    assert response.ok

    # we now get a view
    response = api_client.get_allocation(orderid)
    assert response.json()[0]["batchref"] == earlier_batch

    subscription = redis_client.subscribe_to("line_allocated")

    redis_client.publish_message(
        "change_batch_quantity", {"batchref": earlier_batch, "qty": 5}
    )

    messages = []
    for attempt in Retrying(stop=stop_after_delay(3), reraise=True):
        with attempt:
            message = subscription.get_message(timeout=1)
            if message:
                messages.append(message)
                print(messages)
            data = json.loads(messages[-1]["data"])

    assert data["orderid"] == orderid
    assert data["batchref"] == later_batch
