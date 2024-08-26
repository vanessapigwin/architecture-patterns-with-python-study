import pytest
from allocation.domain import events, commands
from allocation.adapters import repository
from allocation.domain.model import Product
from allocation.service_layer import unit_of_work, messagebus, handlers
from conftest import today, tomorrow, later


class FakeRepository(repository.AbstractRepository):
    def __init__(self, products):
        super().__init__()
        self._products = set(products)

    def _add(self, product):
        self._products.add(product)

    def _get(self, sku):
        return next((p for p in self._products if p.sku == sku), None)

    def _get_by_batchref(self, batchref) -> Product:
        return next(
            (p for p in self._products for b in p.batches if b.reference == batchref),
            None,
        )


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
        messagebus.handle(commands.CreateBatch("b1", "ties", 100, None), uow)
        assert uow.products.get("ties")
        assert uow.committed

    def test_add_batch_for_existing_product(self):
        uow = FakeUnitOFWork()
        messagebus.handle(commands.CreateBatch("b1", "cats", 100, None), uow)
        messagebus.handle(commands.CreateBatch("b2", "cats", 2, None), uow)

        assert "b2" in [b.reference for b in uow.products.get("cats").batches]


class TestAllocate:
    def test_allocate_returns_allocation(self):
        uow = FakeUnitOFWork()
        messagebus.handle(commands.CreateBatch("b1", "penguin", 100, None), uow)
        result = messagebus.handle(commands.Allocate("o1", "penguin", 10), uow)
        assert result.pop(0) == "b1"

    def test_error_for_invalid_sku(self):
        uow = FakeUnitOFWork()
        messagebus.handle(commands.CreateBatch("b1", "realsku", 100, None), uow)

        with pytest.raises(handlers.InvalidSku, match="Invalid sku"):
            messagebus.handle(commands.Allocate("b1", "fakesku", 2), uow)

    def test_commits(self):
        uow = FakeUnitOFWork()
        messagebus.handle(commands.CreateBatch("b1", "ant", 100, None), uow)
        messagebus.handle(commands.Allocate("o1", "ant", 10), uow)
        assert uow.committed


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        uow = FakeUnitOFWork()
        messagebus.handle(
            commands.CreateBatch("batch1", "penguin-cute", 100, None), uow
        )
        [batch] = uow.products.get(sku="penguin-cute").batches
        assert batch.available_quantity == 100

        messagebus.handle(commands.ChangeBatchQuantity("batch1", 50), uow)
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self):
        uow = FakeUnitOFWork()
        event_history = [
            commands.CreateBatch("batch1", "cat-table", 50, None),
            commands.CreateBatch("batch2", "cat-table", 50, today),
            commands.Allocate("o1", "cat-table", 20),
            commands.Allocate("o2", "cat-table", 20),
        ]
        for e in event_history:
            messagebus.handle(e, uow)
        [batch1, batch2] = uow.products.get(sku="cat-table").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        messagebus.handle(commands.ChangeBatchQuantity("batch1", 25), uow)
        # order1 or order2 deallocated, get 25 - 20
        assert batch1.available_quantity == 5
        # 20 reallocated to next batch
        assert batch2.available_quantity == 30
