from typing import cast

from django.core.files.uploadedfile import UploadedFile as DjangoUploadedFile
from django.http import HttpRequest
from ninja import File, Form, Router
from ninja.files import UploadedFile

from apps.warehouse.core.schemas.certification import (
    CertificationFormSchema,
    DeleteCertificationResponse,
    GetAvailableCertificationsResponse,
    GetCertificationItemsResponse,
    GetCertificationResponse,
    GetCertificationsResponse,
)
from apps.warehouse.core.services.certifications import certifications_service
from apps.warehouse.core.transformation import (
    certification_orm_to_schema,
    warehouse_item_orm_to_schema,
)

routes = Router(tags=["certifications"])


def _resolve_file(request: HttpRequest, attachment: UploadedFile | None):
    return attachment or cast(
        DjangoUploadedFile | None, request.FILES.get("attachment")
    )


@routes.get("", response={200: GetCertificationsResponse})
def get_certifications(request: HttpRequest, search_term: str | None = None):
    return GetCertificationsResponse(
        data=[
            certification_orm_to_schema(c)
            for c in certifications_service.get_certifications(search_term)
        ]
    )


@routes.get("/available", response={200: GetAvailableCertificationsResponse})
def get_available_certifications(request: HttpRequest, product_code: str):
    """Certified goods in stock for the given product (picker for outbound rows)."""
    return GetAvailableCertificationsResponse(
        data=certifications_service.get_available_for_product(product_code)
    )


@routes.post("", response={200: GetCertificationResponse})
def create_certification(
    request: HttpRequest,
    body: Form[CertificationFormSchema],
    attachment: File[UploadedFile] | None = None,
):
    certification = certifications_service.create_certification(
        body, _resolve_file(request, attachment)
    )
    return GetCertificationResponse(data=certification_orm_to_schema(certification))


@routes.get("/{certification_id}", response={200: GetCertificationResponse})
def get_certification(request: HttpRequest, certification_id: int):
    return GetCertificationResponse(
        data=certification_orm_to_schema(
            certifications_service.get_certification(certification_id)
        )
    )


@routes.get("/{certification_id}/items", response={200: GetCertificationItemsResponse})
def get_certification_items(request: HttpRequest, certification_id: int):
    """Reverse view: warehouse items (batches) carrying this certification."""
    return GetCertificationItemsResponse(
        data=[
            warehouse_item_orm_to_schema(item)
            for item in certifications_service.get_stock_items(certification_id)
        ]
    )


@routes.post("/{certification_id}", response={200: GetCertificationResponse})
def update_certification(
    request: HttpRequest,
    certification_id: int,
    body: Form[CertificationFormSchema],
    attachment: File[UploadedFile] | None = None,
):
    """Multipart update (POST - file uploads are not parsed on PUT)."""
    certification = certifications_service.update_certification(
        certification_id, body, _resolve_file(request, attachment)
    )
    return GetCertificationResponse(data=certification_orm_to_schema(certification))


@routes.delete("/{certification_id}", response={200: DeleteCertificationResponse})
def delete_certification(request: HttpRequest, certification_id: int):
    certifications_service.delete_certification(certification_id)
    return DeleteCertificationResponse()
