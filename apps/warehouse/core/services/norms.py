"""Norm catalogue (DIN / ISO / CSN) and parsing of legacy norm strings"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Q, QuerySet

from apps.warehouse.core.exceptions import NotFoundException, WarehouseGenericError
from apps.warehouse.core.schemas.norm import NormCreateOrUpdateSchema
from apps.warehouse.models.product import Norm, NormType

# When a product carries several norms, the first of these becomes its default one
PRIMARY_NORM_PRIORITY = (NormType.DIN, NormType.CSN, NormType.ISO)

# "DIN 84", "DIN_84", "DIN84", "CSN_021131", "ISO 4017-A", "DIN EN ISO 4017"
_NORM_TOKEN = re.compile(
    r"(?<![A-Z])(?P<type>DIN|CSN|ISO)[\s_\-]*(?P<glue>(?:(?:EN|ISO|IEC)[\s_\-]+)*)"
    r"(?P<code>\d[0-9A-Z\-./]*)"
)


@dataclass(frozen=True)
class ParsedNorm:
    type: NormType
    code: str

    def __str__(self) -> str:
        return f"{self.type} {self.code}"


def parse_norms(value: str | None) -> list[ParsedNorm]:
    """
    Norms found in a legacy free-text value, in order of appearance (no duplicates).
    The type is the alpha part of the code (the Czech `ČSN` is accepted, too);
    unrecognised values yield an empty list.
    """
    if not value:
        return []
    text = unicodedata.normalize("NFKD", value)
    text = "".join(c for c in text if not unicodedata.combining(c)).upper()

    found: list[ParsedNorm] = []
    for match in _NORM_TOKEN.finditer(text):
        code = match["code"].rstrip("-./")
        types = [NormType(match["type"])]
        # "DIN EN ISO 4017" is the very same item under both DIN and ISO
        if "ISO" in match["glue"] and NormType.ISO not in types:
            types.append(NormType.ISO)
        for norm in (ParsedNorm(t, code) for t in types):
            if code and norm not in found:
                found.append(norm)
    return found


def pick_primary(norms: list[ParsedNorm]) -> ParsedNorm:
    """DIN first, then CSN, then ISO; the first one found of the winning type"""
    return min(norms, key=lambda n: PRIMARY_NORM_PRIORITY.index(n.type))


class NormsService:
    @staticmethod
    def list_norms(
        search_term: str | None = None, norm_type: str | None = None
    ) -> QuerySet[Norm]:
        qs = Norm.objects.prefetch_related("equivalents")
        if norm_type:
            qs = qs.filter(type=norm_type)
        if search_term:
            term = search_term.strip()
            # "DIN 84" should find the norm, too
            compact = re.sub(r"[\s_]+", "", term).upper()
            qs = qs.filter(
                Q(code__icontains=term)
                | Q(type__icontains=term)
                | Q(code__icontains=compact)
                | _label_match(compact)
            )
        return qs

    @staticmethod
    def get(norm_id: int) -> Norm:
        try:
            return Norm.objects.prefetch_related("equivalents").get(pk=norm_id)
        except Norm.DoesNotExist:
            raise NotFoundException(f"Norm {norm_id} not found") from None

    @staticmethod
    @transaction.atomic
    def create(params: NormCreateOrUpdateSchema) -> Norm:
        try:
            norm = Norm.objects.create(code=params.code, type=params.type)
        except IntegrityError:
            raise _duplicate(params) from None
        NormsService._set_equivalents(norm, params.equivalent_ids)
        return NormsService.get(norm.pk)

    @staticmethod
    def get_or_create(norm_type: str, code: str) -> Norm:
        """The norm of the (type, code) pair - created when the catalogue lacks it"""
        norm, _ = Norm.objects.get_or_create(type=norm_type, code=code.strip())
        return norm

    @staticmethod
    @transaction.atomic
    def update(norm_id: int, params: NormCreateOrUpdateSchema) -> Norm:
        norm = NormsService.get(norm_id)
        norm.code, norm.type = params.code, params.type
        try:
            with transaction.atomic():
                norm.save()
        except IntegrityError:
            raise _duplicate(params) from None
        NormsService._set_equivalents(norm, params.equivalent_ids)
        return NormsService.get(norm.pk)

    @staticmethod
    def delete(norm_id: int) -> None:
        NormsService.get(norm_id).delete()

    @staticmethod
    def _set_equivalents(norm: Norm, equivalent_ids: list[int]) -> None:
        ids = set(equivalent_ids) - {norm.pk}
        found = set(Norm.objects.filter(pk__in=ids).values_list("pk", flat=True))
        if missing := ids - found:
            raise WarehouseGenericError(f"Unknown norms: {sorted(missing)}")
        norm.equivalents.set(found)


def _label_match(compact: str) -> Q:
    """`DIN84` matches the (type, code) pair `DIN` + `84`"""
    q = Q()
    for norm_type in NormType.values:
        if compact.startswith(norm_type) and len(compact) > len(norm_type):
            q |= Q(type=norm_type, code__icontains=compact[len(norm_type) :])
    return q


def _duplicate(params: NormCreateOrUpdateSchema) -> WarehouseGenericError:
    return WarehouseGenericError(f"Norm {params.type} {params.code} already exists")


norms_service = NormsService()
