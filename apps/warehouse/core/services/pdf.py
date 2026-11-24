# Resources a document may pull in. Never `file:` - templates are user editable and
# must not be able to embed files of the server.
ALLOWED_RESOURCE_PROTOCOLS = frozenset({"http", "https", "data"})


def print_html_to_pdf(content_html: str) -> bytes:
    # lazy import if requried binaries are missing
    from weasyprint import HTML  # type: ignore
    from weasyprint.urls import URLFetcher  # type: ignore

    return HTML(
        string=content_html,
        url_fetcher=URLFetcher(allowed_protocols=ALLOWED_RESOURCE_PROTOCOLS),
    ).write_pdf()
