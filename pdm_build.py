from pdm.backend.base import Context
from pdm.backend.wheel import WheelBuilder
from pathlib import Path
from typing import Any
import sys


def pdm_build_hook_enabled(context: Context):
    return context.target == "wheel"

def pdm_build_finalize(context: Context, artifact: Path) -> None:
    if isinstance(context.builder, WheelBuilder):
        name_version = context.builder.name_version
        tag = context.builder.tag.replace("py3", f"py{sys.version_info.major}{sys.version_info.minor}")
        artifact.rename(artifact.parent/f"{name_version}-{tag}.whl")
                    