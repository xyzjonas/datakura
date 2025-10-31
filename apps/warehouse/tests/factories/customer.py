import factory
from factory.django import DjangoModelFactory
from faker import Faker

from apps.warehouse.models.customer import CustomerGroup, Customer, ContactPerson

from .user import UserFactory


fake = Faker()


class CustomerGroupFactory(DjangoModelFactory):
    """Factory for CustomerGroup model"""

    class Meta:
        model = CustomerGroup
        django_get_or_create = ("code",)

    code = factory.Sequence(lambda n: f"CG{n:04d}")
    name = factory.Faker("company")


class CustomerFactory(DjangoModelFactory):
    """Factory for Customer model"""

    class Meta:
        model = Customer
        django_get_or_create = ("code",)

    # Basic Information
    name = factory.Faker("company")
    email = factory.Faker("company_email")
    phone = factory.Faker("phone_number")
    code = factory.Sequence(lambda n: f"CUST{n:06d}")

    # Address
    street = factory.Faker("street_address")
    city = factory.Faker("city")
    postal_code = factory.Faker("postcode")
    state = "CZ"

    # Tax Information
    tax_identification = factory.Sequence(lambda n: f"CZ{n:08d}")
    identification = factory.Sequence(lambda n: f"{n:08d}")

    # Business Settings
    customer_type = "FIRMY"
    price_type = "FIRMA"
    invoice_due_days = 30
    block_after_due_days = 30

    # Agreements
    data_collection_agreement = True
    marketing_data_use_agreement = False

    # Status Fields
    is_valid = True
    is_deleted = False

    # Relationships
    owner = factory.SubFactory(UserFactory)
    responsible_user = factory.SubFactory(UserFactory)
    customer_group = factory.SubFactory(CustomerGroupFactory)

    # Additional Fields
    note = factory.Faker("text", max_nb_chars=200)
    register_information = factory.Faker("text", max_nb_chars=150)


class CustomerFactoryMinimal(DjangoModelFactory):
    """Minimal Customer factory without optional fields"""

    class Meta:
        model = Customer
        django_get_or_create = ("code",)

    name = factory.Faker("company")
    code = factory.Sequence(lambda n: f"CUST{n:06d}")
    customer_type = "FIRMY"
    price_type = "FIRMA"
    customer_group = factory.SubFactory(CustomerGroupFactory)


class ContactPersonFactory(DjangoModelFactory):
    """Factory for ContactPerson model"""

    class Meta:
        model = ContactPerson

    # Name components
    title_pre = factory.Iterator(["Ing.", "Mgr.", "Bc.", "Dr.", ""])
    first_name = factory.Faker("first_name")
    middle_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    title_post = factory.Iterator(["Ph.D.", "CSc.", "MBA", ""])

    # Contact information
    email = factory.Faker("email")
    phone = factory.Faker("phone_number")
    birth_date = factory.Faker("date_of_birth", minimum_age=18, maximum_age=80)

    # Address
    street = factory.Faker("street_address")
    city = factory.Faker("city")
    postal_code = factory.Faker("postcode")
    state = "CZ"

    # Relationships
    customer = factory.SubFactory(CustomerFactory)

    # Profile picture
    profile_picture_url = factory.Faker("image_url")

    # Status
    is_deleted = False

    # Additional
    note = factory.Faker("text", max_nb_chars=100)


class ContactPersonFactoryMinimal(DjangoModelFactory):
    """Minimal ContactPerson factory without optional fields"""

    class Meta:
        model = ContactPerson

    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    customer = factory.SubFactory(CustomerFactory)


# Trait examples for more flexible factory usage
class CustomerFactoryWithContacts(CustomerFactory):
    """Customer factory that creates related contact persons"""

    contact1 = factory.RelatedFactory(
        ContactPersonFactory, factory_related_name="customer"
    )
    contact2 = factory.RelatedFactory(
        ContactPersonFactory, factory_related_name="customer"
    )
