import uuid
import pytest
import requests

from allocation import config
from conftest import random_batchref, random_orderid, random_sku


def post_to_add_batch(ref, sku, qty, eta):
    url = config.get_api_url()
    r = requests.post(
        f"{url}/add_batch", json={"ref": ref, "sku": sku, "qty": qty, "eta": eta}
    )
    assert r.status_code == 201


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_happy_path_returns_201_and_allocated_batch():
    sku, other_sku = random_sku(), random_sku("other")
    earlybatch = random_batchref(1)
    laterbatch = random_batchref(2)
    otherbatch = random_batchref(3)

    post_to_add_batch(laterbatch, sku, 100, "2023-01-01")
    post_to_add_batch(earlybatch, sku, 100, "2020-01-01")
    post_to_add_batch(otherbatch, other_sku, 100, None)
    data = {"orderid": random_orderid(), "sku": sku, "qty": 3}

    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json=data)

    assert r.status_code == 201
    assert r.json()["batch_ref"] == earlybatch


@pytest.mark.usefixtures("postgres_db")
@pytest.mark.usefixtures("restart_api")
def test_unhappy_path_returns_400_and_error_message():
    unknown_sku, orderid = random_sku(), random_orderid()

    data = {"orderid": orderid, "sku": unknown_sku, "qty": 20}
    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json=data)

    assert r.status_code == 400
    assert r.json()["messages"] == f"Invalid sku: {unknown_sku}"
