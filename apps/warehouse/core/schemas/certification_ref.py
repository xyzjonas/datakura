from ninja import Schema


class CertificationRefSchema(Schema):
    """Light reference to a certification (e.g. embedded in a batch)."""

    id: int
    code: str
