from __future__ import annotations

from pathlib import Path

from pdm.backend.base import Context


def pdm_build_hook_enabled(context: Context):
    return context.target == "wheel"


def pdm_build_update_files(context: Context, files: dict[str, Path]) -> None:
    from pyfuture.utils import transfer_file

    build_dir = context.ensure_build_dir()
    package_dir = Path(context.config.build_config.package_dir)
    includes = context.config.build_config.includes
    for include in includes:
        src_path = package_dir / include
        tgt_path = build_dir / include
        for src_file in src_path.glob("**/*.py"):
            tgt_file = tgt_path / src_file.relative_to(src_path)
            files[f"{tgt_file.relative_to(build_dir)}"] = tgt_file
            # TODO: support specific version target
            # transfer_file(src_file, tgt_file, target=sys.version_info[:2])
            transfer_file(src_file, tgt_file, target=(3, 8))
