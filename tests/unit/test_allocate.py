import pytest
from allocation.domain.model import Batch, OrderLine, OutOfStock
from allocation.service_layer.services import allocate
from datetime import date, timedelta


today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


def test_prefers_current_stock_batches_to_shipments():
    in_stock_batch = Batch("in-stock-batch", "PENGUIN-TOY", 100, eta=None)
    shipment_batch = Batch("shipment-batch", "PENGUIN-TOY", 100, eta=tomorrow)
    line = OrderLine("1234", "PENGUIN-TOY", 2)

    allocate(line, [in_stock_batch, shipment_batch])

    assert in_stock_batch.available_quantity == 98
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches():
    earliest_batch = Batch("speedy-batch", "APPLE", 100, eta=today)
    normal_batch = Batch("normal-batch", "APPLE", 100, eta=tomorrow)
    last_batch = Batch("slow-batch", "APPLE", 100, eta=later)
    line = OrderLine("order1", "APPLE", 10)

    allocate(line, [earliest_batch, normal_batch, last_batch])

    assert earliest_batch.available_quantity == 90
    assert normal_batch.available_quantity == 100
    assert last_batch.available_quantity == 100


def test_returns_allocated_batch_reference():
    in_stock_batch = Batch("in-stock-batch", "GOLDEN-HAMMER", 100, eta=None)
    shipment_batch = Batch("shipment-batch", "GOLDEN-HAMMER", 100, eta=tomorrow)
    line = OrderLine("order-ref", "GOLDEN-HAMMER", 10)
    allocation = allocate(line, [in_stock_batch, shipment_batch])

    assert allocation == in_stock_batch.reference


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = Batch("batch", "SPOON", 10, eta=today)
    allocate(OrderLine("order1", "SPOON", 10), [batch])

    with pytest.raises(OutOfStock, match="SPOON"):
        allocate(OrderLine("order2", "SPOON", 1), [batch])
