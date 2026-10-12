from urllib.parse import unquote

from django.urls import converters


class DecodingStringConverter:
    """
    Replacement of Django's built-in `str` path converter that decodes the segment once more.

    Django decodes `%2F` to `/` before URL routing, so a code with a slash (`AB/12`) can never
    match a `/{code}` API route. The frontend therefore encodes API paths twice (`AB%252F12`),
    the server decodes it once (`AB%2F12`) and the segment stays a single path parameter, which
    is decoded here for the second time (`AB/12`).
    """

    regex = "[^/]+"

    def to_python(self, value: str) -> str:
        return unquote(value)

    def to_url(self, value: str) -> str:
        return value


def register_path_converters() -> None:
    # `register_converter` refuses to redefine a built-in converter, hence the direct override
    converters.DEFAULT_CONVERTERS["str"] = DecodingStringConverter()
    converters.get_converters.cache_clear()  # type: ignore[attr-defined]
