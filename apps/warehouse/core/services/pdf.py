def print_html_to_pdf(content_html: str) -> bytes:
    # lazy import if requried binaries are missing
    from weasyprint import HTML  # type: ignore

    return HTML(string=content_html).write_pdf()


def free_space_below(content_html: str, css_class: str) -> int:
    """Pixels between the bottom of the last element with `css_class` and the bottom of
    the printable area of the page it ends up on (0 when it is not in the document).

    Lets a footer be pushed to the bottom of the last page (CSS cannot do this across
    page breaks), the document is laid out once and measured.
    """
    from weasyprint import HTML  # type: ignore

    pages = HTML(string=content_html).render().pages
    if not pages:
        return 0
    page = pages[-1]._page_box  # noqa: SLF001 - the layout tree is the only source
    found = None
    for box in page.descendants():
        classes = getattr(box.element, "attrib", {}).get("class", "").split()
        if box.element is not None and css_class in classes:
            found = box
    if found is None:
        return 0
    area_bottom = page.content_box_y() + page.height
    return max(0, int(area_bottom - (found.position_y + found.margin_height())))
