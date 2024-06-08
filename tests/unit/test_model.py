from allocation.domain.model import Batch, OrderLine
from datetime import date
from test_batches import make_batch_and_line


def test_allocating_to_a_batch_reduces_the_available_quantity():
    batch = Batch("batch-001", "SMALL-TABLE", qty=20, eta=date.today())
    line = OrderLine("order-ref", "SMALL-TABLE", 2)

    batch.allocate(line)
    assert batch.available_quantity == 18


def test_can_allocate_if_available_greater_than_required():
    large_batch, small_line = make_batch_and_line("FLUFFY-PILLOW", 20, 2)
    assert large_batch.can_allocate(small_line)


def test_cannot_allocate_if_available_smaller_than_required():
    small_batch, large_line = make_batch_and_line("FLUFFY-PILLOW", 2, 20)
    assert small_batch.can_allocate(large_line) is False


def test_can_allocate_if_available_equal_to_required():
    batch, line = make_batch_and_line("FLUFFY-PILLOW", 10, 10)
    assert batch.can_allocate(line)


def test_cannot_allocate_if_skus_do_not_match():
    batch = Batch("batch-1", "HARD-BED", 20, eta=None)
    different_sku_line = OrderLine("order1", "FLUFFLY-PILLOW", 1)
    assert batch.can_allocate(different_sku_line) is False
