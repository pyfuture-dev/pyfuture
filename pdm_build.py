from __future__ import annotations

import os
import sys
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdm.backend.hooks.base import Context


def pdm_build_hook_enabled(context: Context):
    if sys.version_info[:2] < (3, 12):
        raise RuntimeError("PyFuture cannot be installed from source for Python < 3.12")
    if context.target == "editable" and not os.path.exists(".pdm-python"):
        with open(".pdm-python", "w") as f:
            f.write(sys.executable)
    return False
