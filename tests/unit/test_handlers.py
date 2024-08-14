import pytest
from allocation.domain import events
from allocation.adapters import repository
from allocation.service_layer import unit_of_work, messagebus
from datetime import date, timedelta


today = date.today()
tomorrow = today + timedelta(days=1)
later = tomorrow + timedelta(days=10)


class FakeRepository(repository.AbstractRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)


class FakeUnitOFWork(unit_of_work.AbstractUnitOfWork):

    def __init__(self):
        self.products = FakeRepository([])
        self.committed = False

    def _commit(self):
        self.committed = True

    def rollback(self):
        pass


class TestAddBatch:
    def test_add_batch_for_new_product(self):
        uow = FakeUnitOFWork()
        messagebus.handle(events.BatchCreated("b1", "ties", 100, None), uow)
        assert uow.products.get("ties")
        assert uow.committed

    def test_add_batch_for_existing_product(self):
        uow = FakeUnitOFWork()
        messagebus.handle(events.BatchCreated("b1", "cats", 100, None), uow)
        messagebus.handle(events.BatchCreated("b2", "cats", 2, None), uow)

        assert "b2" in [b.reference for b in uow.products.get("cats").batches]


class TestAllocate:
    def test_allocate_returns_allocation(self):
        uow = FakeUnitOFWork()
        messagebus.handle(events.BatchCreated("b1", "penguin", 100, None), uow)
        result = messagebus.handle(events.AllocationRequired("o1", "penguin", 10), uow)
        assert result.pop(0) == "b1"

    def test_error_for_invalid_sku(self):
        uow = FakeUnitOFWork()
        result = messagebus.handle(events.BatchCreated("b1", "realsku", 100, None), uow)
        assert result.pop(0) is None


def test_commits():
    uow = FakeUnitOFWork()
    messagebus.handle(events.BatchCreated("b1", "ant", 100, None), uow)
    messagebus.handle(events.AllocationRequired("o1", "ant", 10), uow)
    assert uow.committed
