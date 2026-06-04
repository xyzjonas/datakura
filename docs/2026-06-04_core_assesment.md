Warehouse stock-movement audit — final report

  I ran a thorough analysis: read the models myself, dispatched three parallel deep-audit agents (warehouse service, outbound/picking,
  inbound/snapshots), then verified the most explosive claims by directly reading the cited code. Findings below are deduplicated and
  ranked. Each one names the trigger → mechanism → consequence and gives a fix direction.

  Cross-cutting observation

  select_for_update() does not appear once in the entire warehouse app. Every read-then-mutate against WarehouseItem is unlocked. Every 
  stock mutation outside warehouse.py is suspect — WarehouseMovement rows are only ever written inside warehouse.py (one grep confirms it),
  so any other service that mutates stock is bypassing the audit ledger. These two facts shape most of what follows.

  ---
  CRITICAL — items can actually disappear, double, or get silently quarantined
  
  1. Concurrent picking of the same source item silently double-counts inventory
  
  Location: warehouse.py:909-1051 (assign_outbound_item), :633-683 (_split_outbound_pick_item)

  Trigger: Two operators (two scanner tabs, two phones, a retry mid-network-blip) call assign_outbound_item against the same fungible/batch
  source WarehouseItem X (amount=10), each picking a partial quantity (say 4 units) for two different order lines.

  Mechanism: candidate is read outside any lock at :939. The atomic block at :1010 opens, but _split_outbound_pick_item does item.amount -= 
  requested_amount; item.save() on an in-memory snapshot of candidate.amount. Under default READ COMMITTED, both transactions read
  X.amount=10, both subtract 4 from the stale value, both write X=6, both create a brand-new 4-unit split item, both assign it. The
  OneToOneField does NOT trip because the two new items are different rows.
  
  Consequence: X=6 + Y=4 + Z=4 = 14 units exist where there should be 6. Either phantom inventory was created on paper, or — depending on
  whether shipments physically happen — physical and digital diverge permanently.
  
  Fix: Inside transaction.atomic(), re-fetch with WarehouseItem.objects.select_for_update().get(pk=candidate.pk) and re-validate
  requested_amount <= candidate.amount after the lock. Same pattern needed in _unpack_package and in MovementService.move_item for merge
  paths.
  
  ---
  2. Cancelling an OutboundOrder permanently quarantines every picked item
  
  Location: outbound_orders.py:825-912 (OutboundOrdersService.transition_order)
  
  Trigger: Operator cancels an in-flight outbound order that has already been picked (partially or fully).

  Mechanism: Lines 825-827 just set new_state = CANCELLED; lines 855-912 save the order and write an audit entry. Nothing iterates 
  OutboundWarehouseOrderItem to clear warehouse_item, nothing transitions the OutboundWarehouseOrder, nothing writes an inverse 
  WarehouseMovement. I directly grepped — the only warehouse_item = None writes anywhere are response-payload defaults in barcode_lookup.
  There is no production code path that releases an outbound assignment.
  
  Consequence: The picked items keep outbound_assignment__isnull=False forever. The .available manager excludes them at
  models/warehouse.py:87 permanently. Physical inventory sits in the warehouse but the system reports it as "gone." Operators looking at the
  warehouse view see "stock missing"; reconciliation will never close. The bug is invisible until a year of cancellations has accumulated
  and the discrepancy is reportable in tonnes.

  Fix: Add cancel_outbound_warehouse_order that, atomically: iterates order_items with warehouse_item__isnull=False, clears warehouse_item +
  price_at_shipment, writes inverse WarehouseMovement rows, writes audit entries, transitions warehouse-order state to CANCELLED. Invoke it
  from transition_order when target is CANCELLED.
  
  ---
  3. confirm_draft / confirm_arrival are not idempotent — retries duplicate inventory
  
  Location: warehouse.py:1799-1866 (confirm_draft), warehouse.py:1226-1262 (confirm_arrival)
  
  Trigger: User double-clicks "confirm", or the request times out and the client retries, or transition_order (which is called after the
  atomic block) raises (e.g. a transient DB hiccup, a credit-note cross-service call failure).

  Mechanism: The atomic block at :1817 materialises one WarehouseItem per InboundWarehouseOrderItem and commits. The state transition runs
  at :1854 outside that block. If it fails, the DB now holds: items committed AND state still DRAFT. The only retry guard is at :1802: if 
  state != DRAFT: raise — but state IS still DRAFT, so the guard passes and the loop creates a second copy of every item. Same shape in
  confirm_arrival (atomic at :1238, transition at :1262): retry duplicates InboundWarehouseOrderItem rows.
  
  Consequence: Every retry doubles the inbound. Operationally, the symptom is "I see twice as much in stock as we received."
  
  Fix: Move the state transition and downstream service calls INSIDE the atomic block. Add an idempotency guard at the top: if 
  w_order.items.exists(): raise. Use InboundWarehouseOrder.objects.select_for_update().get(...) so concurrent retries serialize.

  ---
  4. Putaway merges into already-picked items, growing shipments after the fact

  Location: warehouse.py:144-166 (BATCH branch), :204-216 (FUNGIBLE branch), in MovementService.move_item
  
  Trigger: Operator puts away an item to a location that already holds the same batch / same fungible product. That existing item happens to
  be already picked into an open outbound order.

  Mechanism: The merge target is found with new_location.items.filter(batch=item.batch).first() and
  new_location.items.filter(stock_product=..., tracking_level=FUNGIBLE).first() — both use the default objects manager, which does NOT 
  exclude picked items. The merge then does existing.amount += amount; existing.save() and deletes the source.
  
  Consequence: A WarehouseItem that was frozen into an outbound order (outbound_assignment set, price_at_shipment frozen) silently grows.
  The customer is invoiced for the original picked amount but physically receives more. The putaway receipt is destroyed. Accounting drifts
  permanently.
  
  Fix: Use WarehouseItem.physical_stock.filter(location=new_location, ...) (which excludes assigned items) for merge-target lookup. Also
  exclude items belonging to DRAFT/IN_TRANSIT inbounds.
  
  ---
  5. move_item FUNGIBLE split severs order_in — staging stock leaks into the pickable pool

  Location: warehouse.py:226-231 in MovementService.move_item (FUNGIBLE branch, no merge target, partial amount)
  
  Trigger: During putaway, a fungible item is partially moved (e.g. 3 of 10) into a fresh location.

  Mechanism: The BATCH branch at :176-183 correctly propagates order_in=item.order_in, batch=item.batch to the new item. The FUNGIBLE branch
  at :226-231 does not — order_in, source_order_item, batch, package_type are all missing from the WarehouseItem.objects.create(...) call.
  The .available manager's exclusion is order_in__state__in=(DRAFT, IN_TRANSIT), which by SQL NULL semantics does not match rows with 
  order_in IS NULL.
  
  Consequence: A fungible item whose source inbound is still DRAFT or IN_TRANSIT is hidden from .available; the partial split-off piece, by
  losing its order_in link, becomes immediately visible to picking — even though it physically represents un-received / un-confirmed stock.
  Inventory snapshot pricing also fails (receipt_unpriced_line_count++) because source_order_item is null.
  
  Fix: Mirror the BATCH branch — propagate order_in=item.order_in, source_order_item=item.source_order_item, batch=item.batch, 
  package_type=item.package_type on every split, in every branch of move_item.
  
  ---
  6. MovementService.move_item is not transactional itself; safety depends on every caller remembering to wrap it

  Location: warehouse.py:118-263
  
  Trigger: A future caller adds a new entry point that does not wrap move_item in transaction.atomic() (or wraps it incompletely).

  Mechanism: The function performs up to four writes (item.save, item.delete, existing.save, new_item.create) plus audit entries plus the
  final WarehouseMovement.objects.create. Today the only production caller is putaway_item, which does wrap it (:2013). But the
  public-looking movement_service interface carries no contract that callers must do this.

  Consequence: Any future regression — or a partial-failure mid-function combined with a missing atomic in a caller — leaves items
  half-merged, half-split, or moved without an audit ledger entry. Defence in depth is missing.
  
  Fix: Wrap the body of move_item in transaction.atomic(). Nested atomics under the caller's atomic are free in Django.
  
  ---
  HIGH — realistic data-integrity gaps with concrete triggers
  
  7. OutboundWarehouseOrderItem.warehouse_item is on_delete=SET_NULL
  
  Location: models/warehouse.py:388-394
  
  If a WarehouseItem is ever deleted (admin, cleanup script, future inventory-adjustment feature), every order item pointing to it silently
  goes NULL. price_at_shipment stays frozen; _sync_outbound_warehouse_order_state (warehouse.py:870-871) counts assignments by
  warehouse_item__isnull=False, so the order silently regresses from COMPLETED to STARTED with no error and no audit. Fix: change to
  on_delete=PROTECT.
  
  8. WarehouseItem.order_in is on_delete=SET_NULL; the .available manager fails open on NULL
  
  Location: models/warehouse.py:144-151, manager at :80-87
  
  .available uses .exclude(order_in__state__in=(DRAFT, IN_TRANSIT)). By SQL semantics, rows with order_in IS NULL do NOT match the exclude,
  so they DO appear in available. Combined with bug #5 (FUNGIBLE split nulls order_in) this is a live leak. Independently: deleting an
  InboundWarehouseOrder (or its parent via primary_order CASCADE) nullifies the link and exposes formerly-hidden stock. Fix: change to
  on_delete=PROTECT, or invert manager semantics to .filter(order_in__state__in=(visible states...)) | .filter(order_in__isnull=True, 
  allowed_when_null=True) — and explicitly decide what NULL means.

  9. Splits, unpacks, and initial materialisation never write WarehouseMovement
  
  Location: warehouse.py:633-683 (split), :685-746 (unpack), :1817-1854 (initial materialisation), :2173-2214 (offload reparent)

  Each of these mutates WarehouseItem.amount or creates new items, but writes only audit_service entries — never a WarehouseMovement. The
  model docstring promises "Traceability: Tracks the movement of a Load OR a single Item"; reconciliation that sums movements per location
  will not balance against item amounts. The unpacked_from FK is the only provenance link, and it is SET_NULL. Fix: write WarehouseMovement
  rows for every create/split/unpack/reparent (location_from=None or location_from=location_to with a reason field).
  
  10. Inbound cancel from RECEIVING/PUTAWAY leaves materialised items pointing to a CANCELLED inbound — and .available does NOT exclude 
  CANCELLED
  
  Location: orders.py:272-342 (OrdersService.transition_order), manager at models/warehouse.py:80-85

  .available excludes DRAFT and IN_TRANSIT only; CANCELLED is visible. So if you cancel a partially-put-away inbound, the items remain in
  stock under a "did not happen" inbound document and are immediately pickable. Procurement records and physical reality diverge. Fix:
  disallow cancel from RECEIVING/PUTAWAY without explicit item reconciliation, OR route through a credit-note that destroys/returns the
  materialised items.
  
  11. transition_order(action="next") jumps PICKING → SENT with no completeness check
  
  Location: outbound_orders.py:838-843
  
  A user POSTing {"action": "next"} to an order in PICKING transitions it to SENT regardless of whether
  OutboundWarehouseOrderItem.warehouse_item__isnull=False for all lines. Order closes with phantom shipments; unpicked lines linger forever.
  Fix: assert all order items are assigned before allowing PICKING → SENT.

  12. transition_order(target_state=...) branch bypasses editability check

  Location: outbound_orders.py:852-853
  
  The internal-callable target_state=... path skips _assert_order_editable. A CANCELLED transition on a COMPLETED order silently flips state
  and (combined with bug #2) traps every picked item permanently. Fix: route CANCELLED through the explicit cancellation handler from bug
  #2's fix.

  13. recalculate_average_purchase_price uses .available, excluding putaway and picked stock

  Location: warehouse.py:1947
  
  Average purchase price weights (existing × old_price + incoming × new_price) / total. Using .available.total_amount() excludes
  putaway-staged owned inventory and picked-but-unshipped inventory — these are real carrying-cost stock. Every receipt biases the average
  toward the new arrival's price. Financial books drift on every receipt. Fix: use .physical_stock.total_amount() or define a dedicated
  "owned-inventory" manager.
  
  14. Inventory snapshot read happens outside its own atomic block, with no locking
  
  Location: inventory_snapshots.py:170-263 (create_snapshot)
  
  The list(WarehouseItem.physical_stock...) materialises at :170 BEFORE the with transaction.atomic(): at :185. Between the read and the
  line writes, concurrent mutations skew the snapshot. Additionally, physical_stock excludes picked-but-unshipped items (they're physically
  present), so the valuation systematically under-counts owned stock by however much is in active picks. Fix: move the read inside the
  transaction (or document eventual consistency), and consciously pick the right base queryset for valuation.
  
  15. Unpacking a SERIALIZED_PACKAGE leaves an inconsistent partial package
  
  Location: warehouse.py:685-746 (_unpack_package)
  
  After unpacking 3 of a "Box-of-12" package, the source item has package_type="Box-of-12" but amount=9. The package's invariant ("a
  15. Unpacking a SERIALIZED_PACKAGE leaves an inconsistent partial package

  Location: warehouse.py:685-746 (_unpack_package)

  After unpacking 3 of a "Box-of-12" package, the source item has package_type="Box-of-12" but amount=9. The package's invariant ("a
  Box-of-12 contains 12") is broken. The next picker matching by desired_package_type still sees this defective package as eligible. Fix:
  when unpacking from SERIALIZED_PACKAGE, change source tracking_level to SERIALIZED_PIECE and clear package_type.

  ---
  MEDIUM — edge cases, audit asymmetries, precision risk

  - _sync_outbound_warehouse_order_state runs outside the assignment's atomic (warehouse.py:1050). A failure between assignment commit and
  state sync leaves the final-pick completion silently un-fired.
  - Snapshot bucket-key dedup race (inventory_snapshots.py:160-168): exists-check outside the atomic; concurrent scheduled jobs both pass it
  and one fails with IntegrityError mid-transaction (loud failure, not silent corruption, but bad UX).
  - _build_outbound_warehouse_order_items plans against unreserved stock (outbound_orders.py:178-240): two simultaneous order creations can
  plan the same physical items; picking then races (compounding bug #1).
  - OutboundOrder.code is mutated on DRAFT → PICKING transition (outbound_orders.py:856-862): audit entries created in the same atomic refer
  to the new code, breaking any audit grouping by code string.
  - MovementService.move_item merge paths have asymmetric audit (warehouse.py:158-166 vs :184-201 vs :207-216): fungible-merge writes no
  audit on either side; batch-merge writes audit only on the source. Reconciliation between audit log and movement log will mismatch.
  - Zero-amount items never get cleaned up (warehouse.py:656, 701): after every amount -= requested, no if item.amount <= 0: item.delete()
  guard. Phantom zero-amount items accumulate; SERIALIZED_PACKAGE fully unpacked leaves a phantom amount-0 package.
  - Float → Decimal precision bug at warehouse.py:1547-1549: Decimal(sum(float_amounts)) introduces binary noise that leaves microscopic
  residue on source items after splits.
  - move_item has no validation that amount > 0 or amount <= item.amount (:118-130): only safe today because the sole caller passes None;
  the public method is a foot-gun.
  - Inbound unit_price_at_receipt divergence (warehouse.py:1245-1252 vs editing the underlying InboundOrderItem.unit_price): snapshots and
  recomputed averages can disagree.

  ---
  LOW — code smells / display quirks

  - unpacked_from is SET_NULL → with bug #9 (no movement on unpack), provenance is completely erasable.
  - No "unpick" endpoint — once warehouse_item is set, only deletion (which silently severs per bug #7) can release it. Mis-scans become
  permanent.
  - inbound_warehouse_order_item_to_schema pending logic (transformation.py:763-769) and remaining_amount fallback via or (:808-813) —
  display-only quirks; not stock loss but they make the UI lie about completion state.
  - location_orm_to_detail_schema excludes only DRAFT, not IN_TRANSIT (transformation.py:306) — display inconsistency.

  ---
  What I would do first

  The findings cluster into three families. The highest-leverage fixes, in order:

  1. Add select_for_update() to the five hot paths — assign_outbound_item's candidate read, _split_outbound_pick_item's source read,
  _unpack_package's package read, move_item's merge-target read, confirm_draft's warehouse-order read. This single class of change closes
  bugs #1, half of #3, and the race surface under #4 and #6. It costs nothing structurally and is mechanically straightforward.
  2. Build the cancellation handler that bug #2 demands — a single new service method that releases assignments, writes inverse movements,
  transitions warehouse orders, and is invoked from OutboundOrdersService.transition_order and from the inbound cancel path (fixing #10).
  3. Fix MovementService.move_item to propagate order_in/source_order_item/batch/package_type on every split branch, filter merge targets
  through physical_stock, and wrap itself in transaction.atomic (#4, #5, #6). Three small in-function fixes that close the only quiet path
  by which already-shipped product can silently grow.

  Together these three workstreams cover every CRITICAL finding and most HIGH ones, and they're all surgical — no model changes, no
  migrations, no API surface change.

  The structural changes (FK on_delete adjustments for #7 and #8, the WarehouseMovement ledger completeness for #9, the manager-semantics
  fix for order_in IS NULL) are the second wave. They require migrations and tests but they're what makes the system actually safe
  long-term.

● Two findings (#1 concurrent-pick race, #2 cancel-never-releases) I'd treat as production hotfixes — they almost certainly already cause
  the symptoms you're worried about ("items going missing"). The others are realistic but rarer; you can sequence them.

