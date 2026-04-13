from __future__ import annotations

from datetime import date
from typing import Optional

from ninja import Schema
from pydantic import ConfigDict, Field

from apps.warehouse.core.schemas.base import BaseResponse
from .base import BaseSchema, PaginatedResponse


class CustomerGroupSchema(BaseSchema):
    """Schema for CustomerGroup output"""

    code: str
    name: str

    model_config = ConfigDict(from_attributes=True)


class CustomerDiscountGroupSchema(BaseSchema):
    code: str
    name: str
    discount_percent: float
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class ContactPersonSchema(BaseSchema):
    """Schema for ContactPerson output"""

    id: int

    # Name components
    title_pre: Optional[str] = None
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    title_post: Optional[str] = None

    # Contact information
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None

    # Address
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    state: Optional[str] = None

    # Profile picture
    profile_picture_url: Optional[str] = None

    # Status
    is_deleted: bool

    # Additional
    note: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CustomerSchema(BaseSchema):
    """Schema for Customer output"""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    code: str

    # Address
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    state: str

    # Tax Information
    tax_identification: Optional[str] = None
    identification: Optional[str] = None

    # Business Settings
    customer_type: str
    price_type: str
    invoice_due_days: int
    block_after_due_days: int

    # Agreements
    data_collection_agreement: bool
    marketing_data_use_agreement: bool

    # Status Fields
    is_valid: bool
    is_deleted: bool

    # Relationships
    owner: Optional[str] = None
    responsible_user: Optional[str] = None
    group: CustomerGroupSchema
    discount_group: CustomerDiscountGroupSchema | None = None
    contacts: list[ContactPersonSchema] = Field(default_factory=list)

    # Additional Fields
    note: Optional[str] = None
    register_information: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class GetCustomerResponse(BaseResponse):
    data: CustomerSchema


class GetCustomersResponse(PaginatedResponse[CustomerSchema]): ...


class CustomerDiscountGroupAssignSchema(Schema):
    discount_group_code: str | None = None


class CustomerGroupCreateOrUpdateSchema(Schema):
    code: str
    name: str


class GetCustomerGroupResponse(BaseResponse):
    data: CustomerGroupSchema


class GetCustomerGroupsResponse(PaginatedResponse[CustomerGroupSchema]): ...


class ContactPersonCreateOrUpdateSchema(Schema):
    """Schema for creating/updating ContactPerson"""

    # Name components
    title_pre: Optional[str] = None
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    title_post: Optional[str] = None

    # Contact information
    email: Optional[str] = None
    phone: Optional[str] = None
    birth_date: Optional[date] = None

    # Address
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    state: Optional[str] = None

    # Profile picture
    profile_picture_url: Optional[str] = None

    # Status
    is_deleted: bool = False

    # Additional
    note: Optional[str] = None


class CustomerCreateOrUpdateSchema(Schema):
    """Schema for creating/updating Customer"""

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    code: str

    # Address
    street: Optional[str] = None
    city: Optional[str] = None
    postal_code: Optional[str] = None
    state: str = "CZ"

    # Tax Information
    tax_identification: Optional[str] = None
    identification: Optional[str] = None

    # Business Settings
    customer_type: str
    price_type: str
    invoice_due_days: int = 30
    block_after_due_days: int = 30

    # Agreements
    data_collection_agreement: bool = False
    marketing_data_use_agreement: bool = False

    # Status Fields
    is_valid: bool = True
    is_deleted: bool = False

    # Relationships - use group code
    customer_group_code: str

    # Optional relationships
    owner: Optional[str] = None
    responsible_user: Optional[str] = None
    discount_group_code: Optional[str] = None

    # Additional Fields
    note: Optional[str] = None
    register_information: Optional[str] = None
