"""Exercise materialisation with 1,000 overlapping roots and 40,000 stub modules.

The generated roots share the namespace application.service.src.python.common.
Importing modules from the first and last roots keeps the check small while the
wrapper merges the full import view.

Use --scenario materialisation --warm-dependencies to exclude initial fixture
generation and minification from the measurement.
"""

from typing import assert_type

from application.service.src.python.common.module_0_0 import value as first_value
from application.service.src.python.common.module_999_39 import value as last_value

assert_type(first_value, int)
assert_type(last_value, int)
