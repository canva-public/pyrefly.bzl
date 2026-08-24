"""A library which uses both Bazel-supported import roots."""

from generated.records_pb2 import Record
from tests.imports.mixed_roots.application.data_access.src.python.model import normalize


def load(record: Record):
    return normalize(record.value)
