import pytest
from allocation.domain import model
from allocation.adapters import repository
from allocation.service_layer import services, unit_of_work
from datetime import date, timedelta


today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


class FakeRepository(repository.AbstractRepository):
    def __init__(self, products):
        self.products = set(products)

    def add(self, product):
        self.products.add(product)

    def get(self, sku):
        return next((p for p in self.products if p.sku == sku), None)


class FakeUnitOFWork(unit_of_work.AbstractUnitOfWork):

    def __init__(self):
        self.products = FakeRepository([])
        self.committed = False

    def commit(self):
        self.committed = True

    def rollback(self):
        pass


def test_add_batch_for_new_product():
    uow = FakeUnitOFWork()
    services.add_batch("b1", "ties", 100, None, uow)
    assert uow.products.get("ties")
    assert uow.committed


def test_add_batch_for_existing_product():
    uow = FakeUnitOFWork()
    services.add_batch("b1", "cats", 100, None, uow)
    services.add_batch("b2", "cats", 2, None, uow)

    assert "b2" in [b.reference for b in uow.products.get("cats").batches]


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
