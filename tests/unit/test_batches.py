from allocation.domain.model import Batch, OrderLine
from datetime import date


def test_allocating_to_a_batch_reduces_avail_quantity():
    batch = Batch("B001", "item-01", qty=20, eta=date.today())
    line = OrderLine("order1", "item-01", 2)

    batch.allocate(line)

    assert batch.available_quantity == 18


def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, date.today()),
        OrderLine("order-1", sku, line_qty),
    )


def test_can_allocate_if_avail_greater_than_required():
    large_batch, small_line = make_batch_and_line("item", 20, 2)
    assert large_batch.can_allocate(small_line)


def test_cannot_allocate_if_avail_less_than_required():
    small_batch, large_line = make_batch_and_line("item", 2, 20)
    assert not small_batch.can_allocate(large_line)


def test_can_allocate_if_avail_equal_to_required():
    batch, line = make_batch_and_line("item", 2, 2)
    assert batch.can_allocate(line)


def test_cannot_allocate_if_skus_do_not_match():
    batch = Batch("Batch1", "penguin", 20, eta=None)
    diff_sku_line = OrderLine("order2", "dog", 2)
    assert not batch.can_allocate(diff_sku_line)


def test_allocation_is_idempotent():
    batch, line = make_batch_and_line("SOME-PRODUCT", 20, 2)
    batch.allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 18


def test_deallocate():
    batch, line = make_batch_and_line("penguin", 20, 2)
    batch.allocate(line)
    batch.deallocate(line)
    assert batch.available_quantity == 20


def test_can_only_deallocate_allocated_lines():
    batch, unallocated_line = make_batch_and_line("SOME-PRODUCT", 20, 2)
    batch.deallocate(unallocated_line)
    assert batch.available_quantity == 20
