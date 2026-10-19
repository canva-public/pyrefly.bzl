"""Check modules from opposite ends of the generated namespace package."""

from typing import assert_type

from application.service.src.python.common.module_0_0 import value as first_value
from application.service.src.python.common.module_999_39 import value as last_value

assert_type(first_value, int)
assert_type(last_value, int)
