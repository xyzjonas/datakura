from __future__ import annotations

from datetime import datetime

from ninja import Schema

from .base import BaseResponse, BaseSchema, EmptyResponse, MediaFileSchema, Response
from .warehouse import WarehouseItemSchema


class CertificationSchema(BaseSchema):
    id: int
    code: str
    description: str | None = None
    attachment: MediaFileSchema | None = None
    batch_codes: list[str] = []


class CertificationFormSchema(Schema):
    """Multipart form fields - the attachment travels as a separate file part."""

    code: str
    description: str | None = None


class CertificationAttachSchema(Schema):
    """
    Attach a certification to an inbound order item.

    Either reuse an existing standalone certification (`certification_id`) or
    create a new one from `code` / `description` (+ the uploaded file).
    """

    certification_id: int | None = None
    code: str | None = None
    description: str | None = None


class AvailableCertificationSchema(Schema):
    """Certified stock of a single product - one row per certified batch."""

    id: int
    code: str
    description: str | None = None
    attachment: MediaFileSchema | None = None
    ordered_date: datetime
    amount: float
    # Batch (barcode) holding `amount` - used as the `desired_batch` requirement.
    batch_code: str


class GetCertificationResponse(Response[CertificationSchema]): ...


class GetCertificationsResponse(BaseResponse):
    data: list[CertificationSchema]


class GetAvailableCertificationsResponse(BaseResponse):
    data: list[AvailableCertificationSchema]


class GetCertificationItemsResponse(BaseResponse):
    data: list[WarehouseItemSchema]


class DeleteCertificationResponse(EmptyResponse): ...
