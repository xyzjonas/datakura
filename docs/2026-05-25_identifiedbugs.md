# Bugs to be fixed

### 1. Impossible to attach  batch to fungible items [DONE]

warehouse item evidence while receiving (inbound warehouse order) - we can select either package, serialized item
or fungible (no tracking). In addition a batch identifier can be attached to that item.
That is possible even for a fungible item - making it partially trackable. In the UI form however,
this option is bugged out as if the select's value is 'fungible' it automatically skips the server call
and makes the button only close the dialog without making any changes. Correct behavior is that if 'batch'
is applied to a fungible item, proper server calls have to be made rendering a preview and POSTing the evidence change
to the backend when hitting the 'evidovat' button.

### 2. Unpacked items have to be 'fungible' [DONE]

Unpacking a package (extracting partial amount of items) causes the newly created items to be of type "serialized"
which is wrong. By removing items from a package we create fungible items as it's not possible to keep tracking
them physically without relabeling them (which isn't the default and should be handled in a different way).
So by default newly created items produced by unpacking operation have to be of type 'fungible'.

### 3. Duplicated stock

Complete unpacking (e.g. while transferring from location to location) makes the original stay in stock
and being completely full again. E.g. a package of 10pcs contains only 5 now (5/10), when transferred
by unpacking and selecting 5 as the amount, new non-tracked does get created with 5pcs in it (correct),
BUT the old item stays with 10pcs as the amount - actually inflating the stock by 10pcs! Very serious mistake!

### 4. Picking - allow selection of lesser quantity [DONE]

When picking stock to fulfill an outbound warehouse order I can only select items that have larger or equal quantity
of the product. E.g. customer ordered 10 macbooks and I have a package of 10 laptops with 4 removed previously (6/10)
at one location and a pile of 5 pcs. in another location. I want to pick the 6 from the package (unpacking it) and
after that complete the order with 4 pieces from the 5 pile (reducing the pile 5 -> 1). Order is fullfilled and only
one last item is remaining in the warehouse.


### 5. Picking - location stays

When an item is picked in the warehouse outbound order, it's supposed to be 'eliminated' from the warehouse,
audit log even states e.g.: "Moved 1.0000 of 0981-0400-01, from AB-03-02, to None, outbound order V2026070005, item #18"
but then upon inspection the item is still marked as to be present at the original location. Yes, we want to keep ALL
items historically in the database, but the location has to be set to 'None' to indicate it is no longer available.