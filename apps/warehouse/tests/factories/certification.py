import factory
from django.core.files.uploadedfile import SimpleUploadedFile
from factory.django import DjangoModelFactory

from apps.warehouse.models.warehouse import Certification


class CertificationFactory(DjangoModelFactory):
    class Meta:
        model = Certification

    @classmethod
    def it(cls, **kwargs) -> Certification:
        return cls(**kwargs)  # type: ignore

    code = factory.Sequence(lambda n: f"CERT-{n:04d}")
    description = factory.Faker("text", max_nb_chars=50)
    attachment = factory.LazyAttribute(
        lambda o: SimpleUploadedFile(
            f"{o.code}.pdf", b"%PDF-1.4 cert", content_type="application/pdf"
        )
    )
