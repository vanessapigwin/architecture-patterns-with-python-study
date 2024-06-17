from datetime import date, timedelta
from allocation.domain import events
from allocation.domain.model import Product, OrderLine, Batch
from conftest import random_sku

today = date.today()
tomorrow = today + timedelta(days=1)
later = today + timedelta(days=10)


def test_prefers_warehouse_batches_to_shipments():
    sku = random_sku()
    in_stock_batch = Batch("b1", sku, 100, None)
    shipment_batch = Batch("b2", sku, 100, tomorrow)
    product = Product(sku=sku, batches=[in_stock_batch, shipment_batch])
    line = OrderLine("o1", sku, 10)

    allocation = product.allocate(line)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches():
    sku = random_sku()
    shipment_batch = Batch("b2", sku, 100, today)
    in_stock_batch = Batch("b1", sku, 100, None)
    line = OrderLine("o1", sku, 10)
    product = Product(sku, [shipment_batch, in_stock_batch])

    allocation = product.allocate(line)

    assert allocation == in_stock_batch.reference
    assert shipment_batch.available_quantity == 100
    assert in_stock_batch.available_quantity == 90


def test_increment_version_number():
    sku = random_sku()
    line = OrderLine("o1", sku, 10)
    product = Product(sku, [Batch("b1", sku, 100, None)])

    product.version_number = 420
    product.allocate(line)
    assert product.version_number == 421


def test_records_out_of_stock_event_if_cannot_allocate():
    sku = random_sku()
    batch = Batch("b1", sku, 1, None)
    order = OrderLine("o1", sku, 100)
    product = Product(sku, [batch])

    allocation = product.allocate(order)
    assert product.events[-1] == events.OutOfStock(sku=sku)
    assert allocation is None
