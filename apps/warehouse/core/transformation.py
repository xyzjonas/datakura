from apps.warehouse.api.schemas.customer import (
    CustomerSchema,
    CustomerGroupSchema,
    ContactPersonSchema,
)
from apps.warehouse.models.customer import Customer


def customer_orm_to_schema(customer: Customer) -> CustomerSchema:
    return CustomerSchema(
        created=customer.created,
        changed=customer.changed,
        name=customer.name,
        email=customer.email,
        phone=customer.phone,
        code=customer.code,
        street=customer.street,
        city=customer.city,
        postal_code=customer.postal_code,
        state=customer.state,
        tax_identification=customer.tax_identification,
        identification=customer.identification,
        customer_type=customer.customer_type,
        price_type=customer.price_type,
        invoice_due_days=customer.invoice_due_days,
        block_after_due_days=customer.block_after_due_days,
        data_collection_agreement=customer.data_collection_agreement,
        marketing_data_use_agreement=customer.marketing_data_use_agreement,
        is_valid=customer.is_valid,
        is_deleted=customer.is_deleted,
        owner=customer.owner.username if customer.owner else None,
        responsible_user=customer.responsible_user.username
        if customer.responsible_user
        else None,
        group=CustomerGroupSchema.from_orm(customer.customer_group),
        contacts=[
            ContactPersonSchema.from_orm(contact) for contact in customer.contacts.all()
        ],
        note=customer.note,
        register_information=customer.register_information,
    )
