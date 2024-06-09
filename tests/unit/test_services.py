import pytest
from allocation.domain import model
from allocation.adapters.repository import FakeRepository
from allocation.service_layer import services


class FakeSession:
    committed = False

    def commit(self):
        self.committed = True


def test_returns_allocation():
    line = model.OrderLine("o1", "penguin", 10)
    batch = model.Batch("b1", "penguin", 100, eta=None)
    repo = FakeRepository([batch])

    result = services.allocate(line, repo, FakeSession())
    assert result == "b1"


def test_error_for_invalid_sku():
    line = model.OrderLine("o1", "nonexistentsku", 10)
    batch = model.Batch("b1", "realsku", 100, eta=None)
    repo = FakeRepository([batch])

    with pytest.raises(services.InvalidSku, match="Invalid sku: nonexistentsku"):
        services.allocate(line, repo, FakeSession())


def test_commits():
    line = model.OrderLine("o1", "ant", 10)
    batch = model.Batch("b1", "ant", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    services.allocate(line, repo, session)
    assert session.committed


def test_service_add_batch_reflected():
    batch = model.Batch("mybatch", "penguins", 100, eta=None)
    repo = FakeRepository([batch])
    session = FakeSession()

    services.add_batch(batch, repo, session)
    assert session.committed


def test_duplicate_batch_ref_fail(): ...


def test_deallocate_decrements_available_qty():
    repo, session = FakeRepository([]), FakeSession()

    batch = model.Batch("b1", "penguins", 100, eta=None)
    services.add_batch(batch, repo, session)

    line = model.OrderLine("order1", "penguins", 10)
    services.allocate(line, repo, session)
    batch = repo.get(reference="b1")
    assert batch.available_quantity == 90

    services.deallocate(line, repo, session)
    assert batch.available_quantity == 100


def test_deallocate_decrements_correct_qty(): ...


def test_deallocate_unallocated_batch_fail(): ...
