from allocation import config
import requests


def post_to_add_batch(ref, sku, qty, eta):
    url = config.get_api_url()
    r = requests.post(
        f"{url}/add_batch", json={"ref": ref, "sku": sku, "qty": qty, "eta": eta}
    )
    assert r.status_code == 201


def post_to_allocate(ref, sku, qty):
    url = config.get_api_url()
    r = requests.post(f"{url}/allocate", json={"ref": ref, "sku": sku, "qty": qty})
    assert r.status_code == 201
