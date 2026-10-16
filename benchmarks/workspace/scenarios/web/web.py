"""Consume HTTPX and Pydantic with transitive dependencies and a native extension."""

from httpx import Client, Request, Response
from pydantic import BaseModel


class Payload(BaseModel):
    name: str


def parse_response(response: Response) -> Payload:
    """Validate a response through the generated Pydantic dependency view."""
    return Payload.model_validate(response.json())


def make_request(client: Client, url: str) -> Request:
    """Build a request without performing any network I/O."""
    return client.build_request("GET", url)
