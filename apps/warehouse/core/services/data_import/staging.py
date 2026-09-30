"""Temporary storage of uploaded files until the import worker picks them up"""

from django.core.files import File
from django.core.files.storage import default_storage
from loguru import logger

STAGING_DIR = "data-import"


def stage_upload(job_id: str, label: str, file: File) -> str:
    """Streams the upload to storage shared with the worker, returns its path"""
    path = default_storage.save(f"{STAGING_DIR}/{job_id}/{label}.json", file)
    logger.debug("Staged '{}' for job {}", path, job_id)
    return path


def read_staged(path: str) -> bytes:
    with default_storage.open(path, "rb") as staged:
        return staged.read()


def discard_staged(paths: list[str]) -> None:
    for path in paths:
        try:
            default_storage.delete(path)
        except OSError as exc:
            logger.warning("Could not delete staged file '{}': {}", path, exc)
