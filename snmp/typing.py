__all__ = [
    "Any",
    "Callable",
    "Generic",
    "Iterator",
    "Literal",
    "NamedTuple",
    "Optional",
    "Tuple",
    "TypeVar",
    "Union",
    "cast",
    "overload",
]

from typing import Any
from typing import Callable
from typing import Generic
from typing import NamedTuple
from typing import Optional
from typing import TypeVar
from typing import Union
from typing import cast
from typing import overload

import sys
if sys.version_info[:2] >= (3, 9):
    from collections.abc import Iterator
    from builtins import tuple as Tuple
else:
    from typing import Iterator
    from typing import Tuple

if sys.version_info[:2] >= (3, 8):
    from typing import Literal
else:
    class DummyType:
        def __getitem__(self, key):
            return None

    Literal = DummyType()
