import pytest
from allocation.domain import model
from allocation.adapters import repository
from allocation.service_layer import services, unit_of_work
from datetime import date, timedelta


today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


class FakeRepository(repository.AbstractRepository):
    def __init__(self, batches):
        self._batches = set(batches)

    def add(self, batch):
        self._batches.add(batch)

    def get(self, reference):
        return next(b for b in self._batches if b.reference == reference)

    def list(self):
        return list(self._batches)


class FakeUnitOFWork(unit_of_work.AbstractUnitOfWork):

    def __init__(self):
        self.batches = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_allocate_returns_allocation():
    uow = FakeUnitOFWork()
    services.add_batch("b1", "penguin", 100, None, uow)
    result = services.allocate("o1", "penguin", 10, uow)
    assert result == "b1"


def test_error_for_invalid_sku():
    uow = FakeUnitOFWork()
    services.add_batch("b1", "realsku", 100, None, uow)

    with pytest.raises(services.InvalidSku, match="Invalid sku: nonexistentsku"):
        services.allocate("o1", "nonexistentsku", 10, uow)


def test_commits():
    uow = FakeUnitOFWork()
    services.add_batch("b1", "ant", 100, None, uow)
    services.allocate("o1", "ant", 10, uow)
    assert uow.committed


def test_service_add_batch_reflected():
    uow = FakeUnitOFWork()
    services.add_batch("mybatch", "penguins", 100, None, uow)
    assert uow.batches.get("mybatch")
    assert uow.committed


def test_deallocate_decrements_available_qty():
    uow = FakeUnitOFWork()
    services.add_batch("b1", "penguins", 100, None, uow)
    services.allocate("order1", "penguins", 10, uow)
    batch = uow.batches.get(reference="b1")
    assert batch.available_quantity == 90

    services.deallocate("b1", "order1", "penguins", 10, uow)
    assert batch.available_quantity == 100


def test_prefers_current_stock_batches_to_shipments():
    in_stock_batch = model.Batch("in-stock-batch", "PENGUIN-TOY", 100, None)
    shipment_batch = model.Batch("shipment-batch", "PENGUIN-TOY", 100, tomorrow)
    line = model.OrderLine("1234", "PENGUIN-TOY", 2)
    model.allocate(line, [in_stock_batch, shipment_batch])

    assert in_stock_batch.available_quantity == 98
    assert shipment_batch.available_quantity == 100


def test_prefers_warehouse_batches_to_shipment():
    uow = FakeUnitOFWork()
    services.add_batch("in-stock-batch", "clock", 100, None, uow)
    services.add_batch("shipment-batch", "clock", 100, tomorrow, uow)
    services.allocate("oref", "clock", 10, uow)
    in_stock_batch = uow.batches.get("in-stock-batch")
    shipment_batch = uow.batches.get("shipment-batch")

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches():
    earliest_batch = model.Batch("speedy-batch", "APPLE", 100, today)
    normal_batch = model.Batch("normal-batch", "APPLE", 100, tomorrow)
    last_batch = model.Batch("slow-batch", "APPLE", 100, later)
    line = model.OrderLine("order1", "APPLE", 10)

    model.allocate(line, [earliest_batch, normal_batch, last_batch])

    assert earliest_batch.available_quantity == 90
    assert normal_batch.available_quantity == 100
    assert last_batch.available_quantity == 100


def test_returns_allocated_batch_reference():
    in_stock_batch = model.Batch("in-stock-batch", "GOLDEN-HAMMER", 100, None)
    shipment_batch = model.Batch("shipment-batch", "GOLDEN-HAMMER", 100, tomorrow)
    line = model.OrderLine("order-ref", "GOLDEN-HAMMER", 10)
    allocation = model.allocate(line, [in_stock_batch, shipment_batch])

    assert allocation == in_stock_batch.reference


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = model.Batch("batch", "SPOON", 10, today)
    model.allocate(model.OrderLine("order1", "SPOON", 10), [batch])

    with pytest.raises(model.OutOfStock, match="SPOON"):
        model.allocate(model.OrderLine("order2", "SPOON", 1), [batch])
