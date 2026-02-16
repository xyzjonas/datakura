import enum
from typing import NoReturn


class ErrorCode(enum.Enum):
    GENERIC_ERROR = ("GEN_0000", "Unknown generic error")
    NOT_FOUND = ("NOT_FOUND_0001", "Not found")

    INVALID_CONVERSION = ("PACKAGING_0001", "Invalid conversion")

    GENERIC_WAREHOUSE_ERROR = ("WAR_0000", "WarehouseItem: bad request")
    INVALID_WAREHOUSE_ITEM = ("WAR_0001", "WarehouseItem: bad request")
    WAREHOUSE_ITEM_NOT_FOUND = ("WAR_0002", "WarehouseItem: not found")
    WAREHOUSE_ITEM_NOT_EDITABLE = ("WAR_0003", "WarehouseOrder: read only")

    @property
    def code(self):
        return self.value[0]

    @property
    def default_message(self):
        return self.value[1]


class TrackableException(Exception):
    code: ErrorCode = ErrorCode.GENERIC_ERROR


class ApiBaseException(TrackableException):
    code: ErrorCode = ErrorCode.GENERIC_ERROR
    http_status: int = 500

    def __init__(self, message: str, http_status: int | None = None):
        if http_status:
            self.http_status = http_status
        super().__init__(message)


class NotFoundException(ApiBaseException):
    code = ErrorCode.NOT_FOUND
    http_status = 404


class WarehouseGenericError(ApiBaseException):
    code = ErrorCode.GENERIC_WAREHOUSE_ERROR
    http_status = 400


class WarehouseItemBadRequestError(ApiBaseException):
    code = ErrorCode.INVALID_WAREHOUSE_ITEM
    http_status = 400


class WarehouseItemNotFoundError(ApiBaseException):
    code = ErrorCode.WAREHOUSE_ITEM_NOT_FOUND
    http_status = 404


class WarehouseOrderNotEditableError(ApiBaseException):
    code = ErrorCode.WAREHOUSE_ITEM_NOT_EDITABLE
    http_status = 400


def raise_by_code(code: ErrorCode, message: str) -> NoReturn:
    exc = ApiBaseException(message)
    exc.code = code
    raise exc
