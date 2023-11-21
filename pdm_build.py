from pdm.backend.base import Context
import sys


def pdm_build_hook_enabled(context: Context):
    return context.target == "wheel"


def pdm_build_initialize(context: Context) -> None:
    config_settings = context.builder.config_settings
    config_settings[
        "--python-tag"
    ] = f"py{sys.version_info.major}{sys.version_info.minor}"
