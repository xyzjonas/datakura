from __future__ import annotations

from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, QuerySet

from apps.warehouse.core.exceptions import ApiBaseException
from apps.warehouse.core.schemas.printer import (
    PrinterCreateOrUpdateSchema,
    PrinterSchema,
)
from apps.warehouse.core.transformation import printer_orm_to_schema
from apps.warehouse.models.printer import Printer, UserAppSettings


class PrintersService:
    @staticmethod
    def get_printers(search_term: str | None = None) -> QuerySet[Printer]:
        qs = Printer.objects.all()
        if search_term:
            qs = qs.filter(
                Q(code__icontains=search_term) | Q(description__icontains=search_term)
            )
        return qs.order_by("code")

    @staticmethod
    @transaction.atomic
    def create_printer(params: PrinterCreateOrUpdateSchema) -> PrinterSchema:
        if Printer.objects.filter(code=params.code).exists():
            raise ApiBaseException(
                "Printer with this code already exists", http_status=400
            )

        printer = Printer.objects.create(
            code=params.code,
            description=params.description,
        )
        return printer_orm_to_schema(printer)

    @staticmethod
    @transaction.atomic
    def update_printer(code: str, params: PrinterCreateOrUpdateSchema) -> PrinterSchema:
        printer = Printer.objects.get(code=code)

        if params.code != code and Printer.objects.filter(code=params.code).exists():
            raise ApiBaseException(
                "Printer with this code already exists", http_status=400
            )

        printer.code = params.code
        printer.description = params.description
        printer.save(update_fields=["code", "description", "changed"])
        return printer_orm_to_schema(printer)

    @staticmethod
    @transaction.atomic
    def delete_printer(code: str) -> PrinterSchema:
        printer = Printer.objects.get(code=code)
        schema = printer_orm_to_schema(printer)
        printer.delete()
        return schema

    @staticmethod
    @transaction.atomic
    def set_default_printer(
        user: User,
        printer_code: str | None,
    ) -> PrinterSchema | None:
        settings_obj, _ = UserAppSettings.objects.select_related(
            "default_printer"
        ).get_or_create(
            user=user,
        )

        if not printer_code:
            settings_obj.default_printer = None
            settings_obj.save(update_fields=["default_printer", "changed"])
            return None

        printer = Printer.objects.get(code=printer_code)
        settings_obj.default_printer = printer
        settings_obj.save(update_fields=["default_printer", "changed"])
        return printer_orm_to_schema(printer)

    @staticmethod
    def get_default_printer(user: User) -> PrinterSchema | None:
        settings_obj = (
            UserAppSettings.objects.select_related("default_printer")
            .filter(user=user)
            .first()
        )
        if not settings_obj or not settings_obj.default_printer:
            return None
        return printer_orm_to_schema(settings_obj.default_printer)


printers_service = PrintersService()
