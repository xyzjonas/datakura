def print_html_to_pdf(content_html: str) -> bytes:
    # lazy import if requried binaries are missing
    from weasyprint import HTML  # type: ignore

    return HTML(string=content_html).write_pdf()
