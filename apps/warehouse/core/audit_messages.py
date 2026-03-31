from dataclasses import dataclass
from enum import Enum


class AuditLanguage(str, Enum):
    EN = "EN"
    CS = "CS"


@dataclass(frozen=True)
class LocalizedAuditMessage:
    translations: dict[AuditLanguage, str]

    @property
    def EN(self) -> str:
        return self.translations[AuditLanguage.EN]

    @property
    def CS(self) -> str:
        return self.translations[AuditLanguage.CS]

    def by_language(self, language: AuditLanguage) -> str:
        return self.translations[language]


class AuditMessages:
    NEW_INBOUND_ORDER_CREATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "New inbound order created",
            AuditLanguage.CS: "Nová příchozí objednávka byla vytvořena",
        }
    )
    WAREHOUSE_ORDER_UPDATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Warehouse order updated",
            AuditLanguage.CS: "Skladová objednávka byla aktualizována",
        }
    )
    INBOUND_ORDER_STATE_CHANGED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Inbound order state changed from '{old_state}' to '{new_state}'",
            AuditLanguage.CS: "Stav příchozí objednávky se změnil z '{old_state}' na '{new_state}'",
        }
    )
    CREDIT_NOTE_STATE_CHANGED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Credit note state changed from '{old_state}' to '{new_state}'",
            AuditLanguage.CS: "Stav dobropisu se změnil z '{old_state}' na '{new_state}'",
        }
    )
    CREDIT_NOTE_CREATED_FOR_INBOUND_ORDER = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Credit note '{credit_note_code}' created for inbound order",
            AuditLanguage.CS: "Dobropis '{credit_note_code}' byl vytvořen pro příchozí objednávku",
        }
    )
    ITEM_PARTIALLY_MOVED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Item partially moved",
            AuditLanguage.CS: "Položka byla částečně přesunuta",
        }
    )
    ITEM_CREATED_BY_PARTIAL_MOVE = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Created by partial move of a non-fungible item to a new location",
            AuditLanguage.CS: "Vytvořeno částečným přesunem nezaměnitelné položky na nové umístění",
        }
    )
    WAREHOUSE_ORDER_BOUND_TO_PURCHASE_ORDER = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Bound to order '{purchase_order_code}'",
            AuditLanguage.CS: "Svázáno s objednávkou '{purchase_order_code}'",
        }
    )
    ORDER_CODE_REFERENCE = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "{order_code}",
            AuditLanguage.CS: "{order_code}",
        }
    )
    TRACKING_SETUP = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "{order_code}: setting up item tracking -> {tracking_level}",
            AuditLanguage.CS: "{order_code}: nastavení sledování položky -> {tracking_level}",
        }
    )
    WAREHOUSE_ORDER_STATE_CHANGED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Warehouse order state changed from '{old_state}' to '{new_state}'",
            AuditLanguage.CS: "Stav skladové objednávky se změnil z '{old_state}' na '{new_state}'",
        }
    )
    CREDIT_NOTE_CREATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Credit note created",
            AuditLanguage.CS: "Dobropis byl vytvořen",
        }
    )
    ITEM_DISCARDED_TO_CREDIT_NOTE = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Item discarded to credit note",
            AuditLanguage.CS: "Položka byla vyřazena do dobropisu",
        }
    )
    AVERAGE_PURCHASE_PRICE_RECALCULATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Average purchase price recalculated",
            AuditLanguage.CS: "Průměrná nákupní cena byla přepočítána",
        }
    )

    ORDER_CREATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Order created",
            AuditLanguage.CS: "Objednávka byla vytvořena",
        }
    )
    ORDER_UPDATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Order updated",
            AuditLanguage.CS: "Objednávka byla aktualizována",
        }
    )
    PRODUCT_CREATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Product created",
            AuditLanguage.CS: "Produkt byl vytvořen",
        }
    )
    PRODUCT_UPDATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Product updated",
            AuditLanguage.CS: "Produkt byl aktualizován",
        }
    )
    MANUAL_CORRECTION = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Manual correction",
            AuditLanguage.CS: "Ruční oprava",
        }
    )
    INITIAL_STOCK_REGISTRATION = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Initial stock registration",
            AuditLanguage.CS: "Počáteční registrace zásob",
        }
    )
    CORRECTED_QUANTITY = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Corrected quantity",
            AuditLanguage.CS: "Opravené množství",
        }
    )
    WAREHOUSE_ORDER_ADJUSTED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Warehouse order adjusted",
            AuditLanguage.CS: "Skladová objednávka byla upravena",
        }
    )
    CHILD_WAREHOUSE_ORDER_CREATED = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Child warehouse order '{child_code}' created from '{parent_code}'",
            AuditLanguage.CS: "Podřízená příjemka/výdejka '{child_code}' vytvořena z '{parent_code}'",
        }
    )
    ITEM_OFFLOADED_TO_CHILD_ORDER = LocalizedAuditMessage(
        {
            AuditLanguage.EN: "Item offloaded (amount={amount}) to child order '{child_code}'",
            AuditLanguage.CS: "Položka přesunuta (množství={amount}) do podřízené objednávky '{child_code}'",
        }
    )
