"""Consumes both import forms exposed by the transformed dependency."""

from generated.records_pb2 import Record
from tests.imports.mixed_roots.application.data_access.src.python.model import normalize


def load(record: Record) -> str:
    return normalize(record.value)
