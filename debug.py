from typing import Generator


def clone(self, **kwargs) -> Generator[str, None, None]:
    return iter(())
