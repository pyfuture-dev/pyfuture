from loguru import logger
import typer
from pyfuture.utils import transfer_file
from pathlib import Path


def str2tuple(version: str) -> tuple[int, int]:
    """
    Convert a string to a tuple of integers.
    """
    version_info: tuple[int, ...] = tuple(map(int, version.split(".")))
    assert len(version_info) >= 2, "Version must be at least major.minor"
    return version_info[0], version_info[1]


app = typer.Typer()


@app.command()
def transfer(
    src_file: Path,
    tgt_file: Path,
    *,
    target: str = "3.8",
):
    """
    Transfer code from src_file and write to tgt_file.
    """

    transfer_file(src_file, tgt_file, target=str2tuple(target))


@app.command()
def watch(
    src_file: Path,
    tgt_file: Path,
    *,
    target: str = "3.8",
):
    """
    Transfer all python files in src_dir to build_dir, and watch for changes.
    """

    transfer_file(src_file, tgt_file, target=str2tuple(target))

    from watchfiles import watch, Change

    for changes in watch(src_file):
        for mode, path in changes:
            match mode:
                case Change.modified:
                    logger.info("Source file has been modified")
                    transfer_file(Path(path), tgt_file, target=str2tuple(target))
                case Change.deleted:
                    logger.info("Source file has been deleted")
                    break


@app.command()
def transfer_dir(
    src_dir: Path,
    build_dir: Path,
    *,
    target: str = "3.8",
):
    """
    Transfer all python files in src_dir to build_dir.
    """

    for src_file in src_dir.glob("**/*.py"):
        tgt_file = build_dir / src_file.relative_to(src_dir)
        transfer_file(src_file, tgt_file, target=str2tuple(target))


@app.command()
def watch_dir(
    src_dir: Path,
    build_dir: Path,
    *,
    target: str = "3.8",
):
    """
    Transfer all python files in src_dir to build_dir, and watch for changes.
    """

    transfer_dir(src_dir, build_dir, target=target)

    from watchfiles import watch, Change, PythonFilter

    for changes in watch(src_dir, watch_filter=PythonFilter()):
        for mode, path in changes:
            match mode:
                case Change.added | Change.modified:
                    logger.info(f"Created: {path}")
                    tgt_file = build_dir / Path(path).relative_to(src_dir)
                    transfer_file(Path(path), tgt_file, target=str2tuple(target))
                case Change.deleted:
                    logger.info(f"Deleted: {path}")
                    tgt_file = build_dir / Path(path).relative_to(src_dir)
                    tgt_file.unlink()


if __name__ == "__main__":
    app()
