import pytest
import requests
import api_client
from allocation import config


from conftest import random_batchref, random_orderid, random_sku


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_202_and_allocated_batch():
    orderid = random_orderid()
    sku, other_sku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)

    api_client.post_to_add_batch(laterbatch, sku, 100, "2023-01-01")
    api_client.post_to_add_batch(earlybatch, sku, 100, "2020-01-01")
    api_client.post_to_add_batch(otherbatch, other_sku, 100, None)

    r = api_client.post_to_allocate(orderid, sku, qty=3)
    assert r.status_code == 202

    r = api_client.get_allocation(orderid)
    assert r.ok
    assert r.json() == [{"sku": sku, "batchref": earlybatch}]


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, orderid = random_sku(), random_orderid()

    r = api_client.post_to_allocate(orderid, unknown_sku, 20, expect_success=False)
    assert r.status_code == 400
    assert r.json()["messages"] == f"Invalid sku: {unknown_sku}"

    r = api_client.get_allocation(orderid)
    assert r.status_code == 404
