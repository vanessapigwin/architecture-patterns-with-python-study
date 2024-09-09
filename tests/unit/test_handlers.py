import pytest
from allocation.domain import commands
from allocation.adapters import repository, notifications
from allocation.domain.model import Product
from allocation.service_layer import unit_of_work, messagebus, handlers
from allocation import bootstrap
from collections import defaultdict
from conftest import today


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


class FakeNotifications(notifications.AbstractNotifications):

    def __init__(self):
        self.sent = defaultdict(list)

    def send(self, destination, message):
        self.sent[destination].append(message)


def bootstrap_test_app():
    return bootstrap.bootstrap(
        start_orm=False,
        uow=FakeUnitOFWork(),
        notifications=FakeNotifications(),
        publish=lambda *args: None,
    )


class TestNotifications:
    def test_send_email_on_out_of_stock_error(self):
        fake_notif = FakeNotifications()
        bus = bootstrap.bootstrap(
            start_orm=False,
            uow=FakeUnitOFWork(),
            notifications=fake_notif,
            publish=lambda *args: None,
        )
        bus.handle(commands.CreateBatch("b1", "hyped-stuff", 9, None))
        bus.handle(commands.Allocate("o1", "hyped-stuff", 400))
        assert fake_notif.sent["user@mail.com"] == ["Out of stock for hyped-stuff"]


class TestAddBatch:
    def test_add_batch_for_new_product(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "ties", 100, None))
        assert bus.uow.products.get("ties")
        assert bus.uow.committed

    def test_add_batch_for_existing_product(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "cats", 100, None))
        bus.handle(commands.CreateBatch("b2", "cats", 2, None))

        assert "b2" in [b.reference for b in bus.uow.products.get("cats").batches]


class TestAllocate:
    def test_allocate_returns_allocation(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "penguin", 100, None))
        bus.handle(commands.Allocate("o1", "penguin", 10))
        [batch] = bus.uow.products.get("penguin").batches
        assert batch.available_quantity == 90

    def test_error_for_invalid_sku(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "realsku", 100, None))

        with pytest.raises(handlers.InvalidSku, match="Invalid sku"):
            bus.handle(commands.Allocate("b1", "fakesku", 2))

    def test_commits(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("b1", "ant", 100, None))
        bus.handle(commands.Allocate("o1", "ant", 10))
        assert bus.uow.committed


class TestChangeBatchQuantity:
    def test_changes_available_quantity(self):
        bus = bootstrap_test_app()
        bus.handle(commands.CreateBatch("batch1", "penguin-cute", 100, None))
        [batch] = bus.uow.products.get(sku="penguin-cute").batches
        assert batch.available_quantity == 100

        bus.handle(commands.ChangeBatchQuantity("batch1", 50))
        assert batch.available_quantity == 50

    def test_reallocates_if_necessary(self):
        bus = bootstrap_test_app()
        event_history = [
            commands.CreateBatch("batch1", "cat-table", 50, None),
            commands.CreateBatch("batch2", "cat-table", 50, today),
            commands.Allocate("o1", "cat-table", 20),
            commands.Allocate("o2", "cat-table", 20),
        ]
        for e in event_history:
            bus.handle(e)
        [batch1, batch2] = bus.uow.products.get(sku="cat-table").batches
        assert batch1.available_quantity == 10
        assert batch2.available_quantity == 50

        bus.handle(commands.ChangeBatchQuantity("batch1", 25))
        # order1 or order2 deallocated, get 25 - 20
        assert batch1.available_quantity == 5
        # 20 reallocated to next batch
        assert batch2.available_quantity == 30
