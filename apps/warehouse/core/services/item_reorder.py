from django.db.models import QuerySet


def reorder_order_items(items_qs: QuerySet, item_index: int, new_index: int) -> None:
    """
    Move the item at `item_index` to `new_index`, resequencing all other items.

    Items are sorted by their current `index` field.  After the move every item
    gets a fresh 0-based sequential index so the list stays compact.

    Must be called inside a ``transaction.atomic()`` block; the caller should
    also pass a ``select_for_update()`` queryset to prevent concurrent races.
    """
    items = list(items_qs.order_by("index"))

    if not items:
        return

    current_pos = next(
        (i for i, item in enumerate(items) if item.index == item_index), None
    )
    if current_pos is None:
        from django.core.exceptions import ObjectDoesNotExist

        raise ObjectDoesNotExist(f"Order item with index {item_index} does not exist.")

    target_pos = max(0, min(new_index, len(items) - 1))

    if current_pos == target_pos:
        return

    moving_item = items.pop(current_pos)
    items.insert(target_pos, moving_item)

    model = type(moving_item)

    # The (order, index) unique constraint means the final indices can't be
    # written in one pass: bulk_update's UPDATE still applies row by row
    # under the hood, so directly swapping values would momentarily duplicate
    # an index and violate the constraint. Stage every item through indices
    # strictly above the current maximum first - values no row can already
    # hold - then assign the final 0..n-1 sequence once every row has moved
    # out of the way.
    staging_base = max(item.index for item in items) + 1
    for offset, item in enumerate(items):
        item.index = staging_base + offset
    model.objects.bulk_update(items, ["index"])

    for i, item in enumerate(items):
        item.index = i
    model.objects.bulk_update(items, ["index"])
