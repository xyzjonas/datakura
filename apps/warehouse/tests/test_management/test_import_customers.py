import copy
import json
from datetime import date

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.warehouse.core.services.data_import.customer_import import (
    CustomerImportService,
)
from apps.warehouse.core.services.data_import.errors import DataImportError
from apps.warehouse.models.customer import ContactPerson, Customer, CustomerGroup
from apps.warehouse.tests.factories.customer import CustomerGroupFactory
from apps.warehouse.tests.factories.user import UserFactory

SAMPLE = {
    "Id": 2,
    "Code": "ABO",
    "Name": "ABO valve, s.r.o.",
    "Email": "fakturace@abovalve.com",
    "Phone": "",
    "Street": "Dalimilova 285/54",
    "City": "Olomouc",
    "PostalCode": "78335",
    "State": "CZ",
    "Identification": "49609050",
    "TaxIdentification": "CZ49609050",
    "RegisterInformation": None,
    "Note": None,
    "Guid": "2936b77a-5898-4a1a-8ab0-429de198e43a",
    "CreatedOn": "2024-01-05T14:21:08.313039Z",
    "IsValid": True,
    "IsDeleted": False,
    "DataCollectionAgreement": False,
    "MarketingDataUseAgreement": False,
    "PriceTypeCode": "FIRMY",
    "InvoiceDueDays": 60,
    "BlockAfterDueDays": 30,
    "ResponsibleUserEmail": "infomohelnice@stemax.cz",
    "CustomerTypeCode": "COMPANY",
    "CustomerGroupCode": "ODBĚRATEL-STANDARD",
    "People": [
        {
            "TitlePre": None,
            "FirstName": "Jitka",
            "MiddleName": None,
            "LastName": "Miklasová",
            "TitlePost": None,
            "Email": "jitka.miklasova@abovalve.com",
            "Phone": "737314030",
            "BirthDate": None,
            "Street": "Dalimilova 285/54, brána A",
            "City": "Olomouc-Chomoutov",
            "PostalCode": "783 35",
            "State": "CZ",
            "Note": None,
            "CreatedOn": "2025-01-16T08:59:05.270602Z",
        }
    ],
}


def sample(**overrides) -> dict:
    data = copy.deepcopy(SAMPLE)
    data.update(overrides)
    return data


def customers():
    """Customers without the one seeded by migrations"""
    return Customer.objects.exclude(code="ghost-customer")


def groups():
    return CustomerGroup.objects.exclude(code="")


def run(*rows: dict):
    return CustomerImportService().import_from_json(json.dumps(list(rows)))


@pytest.mark.django_db
def test_import_sample_blank_database():
    summary = run(sample())

    assert (summary.created_count, summary.updated_count) == (1, 0)
    assert (summary.contacts_count, summary.groups_created) == (1, 1)
    customer = Customer.objects.get(code="ABO")
    assert customer.name == "ABO valve, s.r.o."
    assert customer.email == "fakturace@abovalve.com"
    assert customer.phone == ""
    assert customer.postal_code == "78335"
    assert customer.tax_identification == "CZ49609050"
    assert customer.identification == "49609050"
    assert customer.customer_type == "FIRMA"
    assert customer.price_type == "FIRMY"
    assert (customer.invoice_due_days, customer.block_after_due_days) == (60, 30)
    assert customer.is_valid and not customer.is_deleted
    assert customer.note is None
    assert customer.customer_group.code == "ODBĚRATEL-STANDARD"
    assert customer.customer_group.name == "ODBĚRATEL-STANDARD"
    # unknown responsible user is created without a usable password
    user = customer.responsible_user
    assert user.email == user.username == "infomohelnice@stemax.cz"
    assert not user.has_usable_password()
    assert summary.users_created == 1
    assert summary.warnings == []

    person = customer.contacts.get()
    assert (person.first_name, person.last_name) == ("Jitka", "Miklasová")
    assert person.phone == "737314030"
    assert person.city == "Olomouc-Chomoutov"
    assert person.state == "CZ"
    assert person.title_pre is None and person.birth_date is None


@pytest.mark.django_db
def test_responsible_user_is_matched_by_email_ignoring_case():
    user = UserFactory(email="infomohelnice@stemax.cz")

    summary = run(sample(ResponsibleUserEmail="InfoMohelnice@Stemax.cz"))

    assert customers().get().responsible_user == user
    assert summary.users_created == 0
    assert summary.warnings == []


@pytest.mark.django_db
def test_responsible_user_is_created_once_for_many_customers():
    summary = run(
        sample(Code="A", ResponsibleUserEmail="new@x.cz"),
        sample(Code="B", ResponsibleUserEmail="NEW@x.cz"),
    )

    assert summary.users_created == 1
    assert User.objects.filter(email__iexact="new@x.cz").count() == 1
    assert {c.responsible_user for c in customers()} == {
        User.objects.get(email="new@x.cz")
    }


@pytest.mark.django_db
def test_import_is_idempotent_and_updates():
    run(sample())
    summary = run(sample(Name="Renamed", InvoiceDueDays=10))

    assert (summary.created_count, summary.updated_count) == (0, 1)
    assert summary.groups_created == 0
    customer = customers().get()
    assert customer.name == "Renamed"
    assert customer.invoice_due_days == 10
    assert customer.contacts.count() == 1
    assert ContactPerson.objects.count() == 1


@pytest.mark.django_db
def test_contact_is_updated_in_place():
    run(sample())
    person = copy.deepcopy(SAMPLE["People"][0])
    person["Phone"] = "111"
    person["BirthDate"] = "1990-05-17"

    run(sample(People=[person]))

    contact = ContactPerson.objects.get()
    assert contact.phone == "111"
    assert contact.birth_date == date(1990, 5, 17)


@pytest.mark.django_db
def test_second_person_is_added():
    other = {**SAMPLE["People"][0], "FirstName": "Petr", "Email": None}

    run(sample(People=[SAMPLE["People"][0], other]))

    assert ContactPerson.objects.count() == 2
    assert ContactPerson.objects.get(first_name="Petr").email == ""


@pytest.mark.django_db
def test_existing_group_is_reused_with_its_name():
    group = CustomerGroupFactory(code="ODBĚRATEL-STANDARD", name="Standard")

    summary = run(sample())

    assert summary.groups_created == 0
    assert customers().get().customer_group == group
    assert groups().get().name == "Standard"


@pytest.mark.django_db
def test_accepts_single_object():
    summary = CustomerImportService().import_from_json(json.dumps(sample()))

    assert summary.created_count == 1


@pytest.mark.django_db
@pytest.mark.parametrize(
    "legacy, expected",
    [("COMPANY", "FIRMA"), ("PERSON", "OSOBA"), ("FIRMA", "FIRMA")],
)
def test_customer_type_mapping(legacy, expected):
    run(sample(CustomerTypeCode=legacy))

    assert customers().get().customer_type == expected


@pytest.mark.django_db
def test_null_and_blank_optionals_are_tolerated():
    run(
        sample(
            Email=None,
            Street=None,
            City=None,
            PostalCode=None,
            State="",
            Identification=None,
            TaxIdentification=None,
            RegisterInformation="",
            ResponsibleUserEmail="",
            IsValid=None,
            DataCollectionAgreement=None,
            People=None,
        )
    )

    customer = customers().get()
    assert customer.state == "CZ"
    assert customer.street == customer.email == customer.identification == ""
    assert customer.register_information is None
    assert customer.is_valid is True
    assert customer.data_collection_agreement is False
    assert customer.contacts.count() == 0


@pytest.mark.django_db
def test_null_and_unknown_settings_fall_back_to_defaults():
    run(
        sample(
            PriceTypeCode=None,
            CustomerTypeCode=None,
            CustomerGroupCode="",
            InvoiceDueDays=None,
            BlockAfterDueDays=None,
        )
    )

    customer = customers().get()
    assert customer.price_type == ""
    assert customer.customer_type == "FIRMA"
    assert customer.invoice_due_days == 14
    assert customer.block_after_due_days == 30
    assert customer.customer_group.code == "default"


@pytest.mark.django_db
@pytest.mark.parametrize("code", [None, ""])
@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("Řezníček s.r.o.", "REZNICEK-S-R-O"),
        ("ALPE  Žluťoučký (kůň) & syn", "ALPE-ZLUTOUCKY-KUN-SYN"),
        ("  Enag.cz  ", "ENAG-CZ"),
    ],
)
def test_missing_code_is_derived_from_name(code, name, expected):
    run(sample(Code=code, Name=name))

    assert customers().get().code == expected


@pytest.mark.django_db
def test_missing_code_and_name_fails():
    with pytest.raises(DataImportError):
        run(sample(Code=None, Name="..."))


@pytest.mark.django_db
@pytest.mark.parametrize("state", ["DE", "NL", "Německo"])
def test_foreign_state_and_unknown_price_type_are_kept(state):
    run(sample(State=state, PriceTypeCode="NEW-PRICE"))

    customer = customers().get()
    assert customer.state == state
    assert customer.price_type == "NEW-PRICE"


@pytest.mark.django_db
def test_nameless_contact_uses_email_as_name_or_is_skipped():
    summary = run(
        sample(
            People=[
                {"FirstName": None, "LastName": "", "Email": "avant@avant.cz"},
                {"FirstName": None, "LastName": None},
                {"FirstName": "A", "LastName": None, "State": "DE"},
            ]
        )
    )

    by_email = customers().get().contacts.get(email="avant@avant.cz")
    assert (by_email.first_name, by_email.last_name) == ("avant@avant.cz", "")
    contact = customers().get().contacts.get(first_name="A")
    assert contact.last_name == "" and contact.state is None
    assert customers().get().contacts.count() == 2
    assert any("without a name or email" in w for w in summary.warnings)


@pytest.mark.django_db
def test_state_sk_is_supported():
    run(sample(State="SK"))

    assert customers().get().state == "SK"


@pytest.mark.django_db
def test_bad_row_rolls_back_everything_and_all_errors_are_reported():
    good = sample(Code="OK")
    bad_code = sample(Code="BAD-1", Name="")
    bad_type = sample(Code="BAD-2", CustomerTypeCode="ALIEN")

    with pytest.raises(DataImportError) as exc:
        run(good, bad_code, bad_type)

    assert "Record #1" in str(exc.value) and "Record #2" in str(exc.value)
    assert not customers().exists()
    assert not groups().exists()


@pytest.mark.django_db
def test_failure_while_writing_rolls_back_previous_rows(monkeypatch):
    def boom(*args, **kwargs):
        raise RuntimeError("db exploded")

    run(sample(Code="EXISTING", CustomerGroupCode="G"))
    monkeypatch.setattr(ContactPerson.objects, "update_or_create", boom)

    with pytest.raises(DataImportError, match="db exploded"):
        run(sample(Code="NEW", Name="changed"), sample(Code="EXISTING", Name="x"))

    assert not Customer.objects.filter(code="NEW").exists()
    assert Customer.objects.get(code="EXISTING").name != "x"


@pytest.mark.django_db
@pytest.mark.parametrize(
    "override",
    [
        {"Code": "C" * 51},
        {"Name": None},
        {"Name": ""},
        {"CustomerTypeCode": "ALIEN"},
        {"InvoiceDueDays": -1},
        {"InvoiceDueDays": "abc"},
        {"PostalCode": "1" * 21},
        {"People": [{"FirstName": "A", "LastName": "B", "BirthDate": "nope"}]},
        {"People": "x"},
    ],
)
def test_invalid_input_raises(override):
    with pytest.raises(DataImportError):
        run(sample(**override))

    assert not customers().exists()


@pytest.mark.django_db
@pytest.mark.parametrize("raw", ["nope", "[{]", "[1]", "[{}]", "null"])
def test_malformed_input_raises(raw):
    with pytest.raises(DataImportError):
        CustomerImportService().import_from_json(raw)


@pytest.mark.django_db
def test_missing_file_raises():
    with pytest.raises(DataImportError, match="Cannot read"):
        CustomerImportService().import_from_path("/nonexistent/customers.json")


@pytest.mark.django_db
def test_command_imports_file(tmp_path, capsys):
    path = tmp_path / "customers.json"
    path.write_text(json.dumps([SAMPLE]), encoding="utf-8-sig")

    call_command("import_customers", file=str(path))

    assert customers().count() == 1
    assert "1 created" in capsys.readouterr().out


@pytest.mark.django_db
def test_command_turns_import_error_into_command_error(tmp_path):
    path = tmp_path / "customers.json"
    path.write_text("[{}]")

    with pytest.raises(CommandError):
        call_command("import_customers", file=str(path))
