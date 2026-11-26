"""
Backfill of `StockProduct.norm` and `customs_declaration_group` from the legacy
product metas (`attributes`).

The metas hold only two kinds of entries: `CUSTOMS_DECLARATION_GROUP` (customs
nomenclature) and anything else, which is a norm - only the value is parsed.
The run is idempotent: values already set on a product are never overwritten.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

from django.db import transaction
from loguru import logger

from apps.warehouse.core.schemas.norm import (
    NormBackfillIssueSchema,
    NormBackfillResultSchema,
)
from apps.warehouse.core.services.data_import.progress import ImportProgress
from apps.warehouse.core.services.norms import ParsedNorm, parse_norms, pick_primary
from apps.warehouse.models.product import Norm, StockProduct

CUSTOMS_META_KEY = "CUSTOMS_DECLARATION_GROUP"
MAX_REPORTED_ISSUES = 500
CHUNK_SIZE = 500


@dataclass
class _Run:
    norms: dict[tuple[str, str], Norm]
    # already linked pairs of norm ids
    pairs: set[frozenset[int]]
    stats: dict[str, int] = field(
        default_factory=lambda: {
            "products_scanned": 0,
            "customs_filled": 0,
            "norms_linked": 0,
            "norms_created": 0,
            "aliases_linked": 0,
            "norms_kept": 0,
            "without_customs": 0,
            "without_norm": 0,
            "invalid_count": 0,
        }
    )
    invalid: list[NormBackfillIssueSchema] = field(default_factory=list)


class NormBackfillService:
    def run(self, progress: ImportProgress | None = None) -> NormBackfillResultSchema:
        progress = progress or ImportProgress()
        run = _Run(
            norms={(n.type, n.code): n for n in Norm.objects.all()},
            pairs={
                frozenset((a, b))
                for a, b in Norm.equivalents.through.objects.values_list(
                    "from_norm_id", "to_norm_id"
                )
            },
        )

        total = StockProduct.objects.count()
        logger.info("Norm backfill started: {} products", total)
        progress.begin_stage("normy", 1)
        progress.set_total(total)

        for product in StockProduct.objects.select_related("norm").iterator(
            chunk_size=CHUNK_SIZE
        ):
            with transaction.atomic():
                self._process(product, run)
            progress.advance()
        progress.end_stage()
        progress.finish()

        logger.info("Norm backfill done: {}", run.stats)
        return NormBackfillResultSchema(
            **run.stats, invalid=run.invalid[:MAX_REPORTED_ISSUES]
        )

    def _process(self, product: StockProduct, run: _Run) -> None:
        run.stats["products_scanned"] += 1
        attributes = product.attributes if isinstance(product.attributes, dict) else {}
        changed: list[str] = []

        customs = str(attributes.get(CUSTOMS_META_KEY) or "").strip()
        if customs and not product.customs_declaration_group:
            product.customs_declaration_group = customs[:255]
            changed.append("customs_declaration_group")
            run.stats["customs_filled"] += 1

        parsed: list[ParsedNorm] = []
        for key, value in attributes.items():
            if key == CUSTOMS_META_KEY:
                continue
            found = parse_norms(str(value))
            if not found:
                self._flag(run, product, key, value)
            parsed.extend(n for n in found if n not in parsed)

        if parsed:
            norms = [self._get_or_create(run, n) for n in parsed]
            self._link_aliases(run, norms)
            if product.norm_id is not None:
                run.stats["norms_kept"] += 1
            else:
                primary = pick_primary(parsed)
                product.norm = run.norms[(primary.type.value, primary.code)]
                changed.append("norm")
                run.stats["norms_linked"] += 1

        if changed:
            product.save(update_fields=[*changed, "changed"])
        if not product.customs_declaration_group:
            run.stats["without_customs"] += 1
        if product.norm_id is None:
            run.stats["without_norm"] += 1

    @staticmethod
    def _flag(run: _Run, product: StockProduct, key: str, value: object) -> None:
        run.stats["invalid_count"] += 1
        if len(run.invalid) < MAX_REPORTED_ISSUES:
            run.invalid.append(
                NormBackfillIssueSchema(
                    product_code=product.code,
                    key=key,
                    value=str(value),
                    reason=(
                        "empty value"
                        if not str(value).strip()
                        else "no known norm (DIN / CSN / ISO) recognised"
                    ),
                )
            )

    @staticmethod
    def _get_or_create(run: _Run, parsed: ParsedNorm) -> Norm:
        key = (parsed.type.value, parsed.code)
        if key not in run.norms:
            run.norms[key], created = Norm.objects.get_or_create(
                type=key[0], code=key[1]
            )
            run.stats["norms_created"] += created
        return run.norms[key]

    @staticmethod
    def _link_aliases(run: _Run, norms: list[Norm]) -> None:
        """
        The norms of one product describe the same item - alias them pairwise
        (across namespaces: two codes of one type are different items).
        """
        for a, b in combinations(norms, 2):
            if a.type == b.type:
                continue
            pair = frozenset((a.pk, b.pk))
            if pair not in run.pairs:
                a.equivalents.add(b)
                run.pairs.add(pair)
                run.stats["aliases_linked"] += 1


norm_backfill_service = NormBackfillService()
