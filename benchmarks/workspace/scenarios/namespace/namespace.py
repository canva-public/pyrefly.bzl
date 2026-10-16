"""Consume packages which share the google namespace across dependency trees."""

from google.api_core.retry import Retry
from google.auth.credentials import AnonymousCredentials
from google.cloud.storage import Client
from google.rpc.status_pb2 import Status

credentials: AnonymousCredentials = AnonymousCredentials()
retry: Retry = Retry()
client: Client = Client(project="pyrefly-benchmark", credentials=credentials)
status: Status = Status()


def object_url(bucket: str, name: str) -> str:
    """Construct an object URL using the storage client's typed interface."""
    return client.bucket(bucket).blob(name).public_url
