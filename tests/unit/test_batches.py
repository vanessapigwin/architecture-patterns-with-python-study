from allocation.domain.model import Batch, OrderLine
from datetime import date


def make_batch_and_line(sku, batch_qty, line_qty):
    return (
        Batch("batch-001", sku, batch_qty, date.today()),
        OrderLine("order-1", sku, line_qty),
    )


def test_can_only_deallocate_allocated_lines():
    batch, unallocated_line = make_batch_and_line("SOME-PRODUCT", 20, 2)
    batch.deallocate(unallocated_line)
    assert batch.available_quantity == 20


def test_allocation_is_idempotent():
    batch, line = make_batch_and_line("SOME-PRODUCT", 20, 2)
    batch.allocate(line)
    batch.allocate(line)
    assert batch.available_quantity == 18
