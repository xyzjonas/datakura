# Bugs to be fixed

### 1. Impossible to attach  batch to fungible items

warehouse item evidence while receiving (inbound warehouse order) - we can select either package, serialized item
or fungible (no tracking). In addition a batch identifier can be attached to that item.
That is possible even for a fungible item - making it partially trackable. In the UI form however,
this option is bugged out as if the select's value is 'fungible' it automatically skips the server call
and makes the button only close the dialog without making any changes. Correct behavior is that if 'batch'
is applied to a fungible item, proper server calls have to be made rendering a preview and POSTing the evidence change
to the backend when hitting the 'evidovat' button.

### 2. Unpacked items have to be 'fungible'

Unpacking a package (extracting partial amount of items) causes the newly created items to be of type "serialized"
which is wrong. By removing items from a package we create fungible items as it's not possible to keep tracking
them physically without relabeling them (which isn't the default and should be handled in a different way).
So by default newly created items produced by unpacking operation have to be of type 'fungible'.

### 3.

Complete unpacking (e.g. while transferring from location to location) makes the original stay in stock
and being completely full again. E.g. a package of 10pcs contains only 5 now (5/10), when transferred
by unpacking and selecting 5 as the amount, new non-tracked does get created with 5pcs in it (correct),
BUT the old item stays with 10pcs as the amount - actually inflating the stock by 10pcs! Very serious mistake!

### 4. TBD
