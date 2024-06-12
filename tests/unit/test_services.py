import pytest
from allocation.domain import model
from allocation.adapters import repository
from allocation.service_layer import services
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


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


def test_allocate_returns_allocation():
    repo, session = FakeRepository([]), FakeSession()

    services.add_batch("b1", "penguin", 100, eta=None, repo=repo, session=session)
    result = services.allocate("o1", "penguin", 10, repo, FakeSession())

    assert result == "b1"


def test_error_for_invalid_sku():
    repo, session = FakeRepository([]), FakeSession()

    services.add_batch("b1", "realsku", 100, eta=None, repo=repo, session=session)

    with pytest.raises(services.InvalidSku, match="Invalid sku: nonexistentsku"):
        services.allocate("o1", "nonexistentsku", 10, repo, FakeSession())


def test_commits():
    repo, session = FakeRepository([]), FakeSession()

    services.add_batch("b1", "ant", 100, eta=None, repo=repo, session=session)
    services.allocate("o1", "ant", 10, repo, session)

    assert session.committed


def test_service_add_batch_reflected():
    repo, session = FakeRepository([]), FakeSession()

    services.add_batch("mybatch", "penguins", 100, eta=None, repo=repo, session=session)
    assert repo.get("mybatch")
    assert session.committed


def test_deallocate_decrements_available_qty():
    repo, session = FakeRepository([]), FakeSession()

    services.add_batch("b1", "penguins", 100, eta=None, repo=repo, session=session)
    services.allocate("order1", "penguins", 10, repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90

    services.deallocate("order1", "penguins", 10, repo, session)
    assert batch.available_quantity == 100


def test_prefers_current_stock_batches_to_shipments():
    in_stock_batch = model.Batch("in-stock-batch", "PENGUIN-TOY", 100, eta=None)
    shipment_batch = model.Batch("shipment-batch", "PENGUIN-TOY", 100, eta=tomorrow)
    line = model.OrderLine("1234", "PENGUIN-TOY", 2)

    model.allocate(line, [in_stock_batch, shipment_batch])

    assert in_stock_batch.available_quantity == 98
    assert shipment_batch.available_quantity == 100


# service layer test
def test_prefers_warehouse_batches_to_shipment():
    in_stock_batch = model.Batch("in-stock-batch", "clock", 100, eta=None)
    shipment_batch = model.Batch("shipment-batch", "clock", 100, eta=tomorrow)

    repo = FakeRepository([in_stock_batch, shipment_batch])
    session = FakeSession()

    services.allocate("oref", "clock", 10, repo, session)

    assert in_stock_batch.available_quantity == 90
    assert shipment_batch.available_quantity == 100


def test_prefers_earlier_batches():
    earliest_batch = model.Batch("speedy-batch", "APPLE", 100, eta=today)
    normal_batch = model.Batch("normal-batch", "APPLE", 100, eta=tomorrow)
    last_batch = model.Batch("slow-batch", "APPLE", 100, eta=later)
    line = model.OrderLine("order1", "APPLE", 10)

    model.allocate(line, [earliest_batch, normal_batch, last_batch])

    assert earliest_batch.available_quantity == 90
    assert normal_batch.available_quantity == 100
    assert last_batch.available_quantity == 100


def test_returns_allocated_batch_reference():
    in_stock_batch = model.Batch("in-stock-batch", "GOLDEN-HAMMER", 100, eta=None)
    shipment_batch = model.Batch("shipment-batch", "GOLDEN-HAMMER", 100, eta=tomorrow)
    line = model.OrderLine("order-ref", "GOLDEN-HAMMER", 10)
    allocation = model.allocate(line, [in_stock_batch, shipment_batch])

    assert allocation == in_stock_batch.reference


def test_raises_out_of_stock_exception_if_cannot_allocate():
    batch = model.Batch("batch", "SPOON", 10, eta=today)
    model.allocate(model.OrderLine("order1", "SPOON", 10), [batch])

    with pytest.raises(model.OutOfStock, match="SPOON"):
        model.allocate(model.OrderLine("order2", "SPOON", 1), [batch])
