from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pdm.backend.hooks.base import Context


def pdm_build_hook_enabled(context: Context):
    if sys.version_info[:2] < (3, 12):
        raise RuntimeError("PyFuture cannot be installed from source for Python < 3.12")
    if context.target == "editable" and not os.path.exists(".pdm-python"):
        with open(".pdm-python", "w") as f:
            f.write(sys.executable)

    return context.target == "wheel"


def pdm_build_initialize(context: Context) -> None:
    from pyfuture.hooks import pdm as pyfuture_pdm_hooks

    hook_config = pyfuture_pdm_hooks.get_hook_config(context)
    target_str = pyfuture_pdm_hooks.get_target_str(hook_config)
    pyfuture_pdm_hooks.pdm_build_initialize(context, target_str)


def pdm_build_update_files(context: Context, files: dict[str, Path]) -> None:
    from pyfuture.hooks import pdm as pyfuture_pdm_hooks
    from pyfuture.utils import get_target

    hook_config = pyfuture_pdm_hooks.get_hook_config(context)
    target_str = pyfuture_pdm_hooks.get_target_str(hook_config)
    target = get_target(target_str)
    pyfuture_pdm_hooks.pdm_build_update_files(context, files, target)
