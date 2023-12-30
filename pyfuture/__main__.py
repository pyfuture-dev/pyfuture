from __future__ import annotations

from pathlib import Path

import typer
from loguru import logger
from rich.console import Console
from rich.highlighter import NullHighlighter
from rich.logging import RichHandler
from rich.style import Style

from pyfuture.utils import transfer_file

app = typer.Typer()


def init_logger(log_level: str):
    handler = RichHandler(console=Console(style=Style()), highlighter=NullHighlighter(), markup=True)
    logger.remove()
    logger.add(handler, format="{message}", level=log_level)


@app.command()
def transfer(src_file: Path, tgt_file: Path, *, target: str = "3.8", log_level: str = "INFO"):
    """
    Transfer code from src_file and write to tgt_file.
    """
    assert target == "3.8", "PyFuture is very early stage, not support target argument yet"
    init_logger(log_level)
    transfer_file(src_file, tgt_file)


@app.command()
def watch(src_file: Path, tgt_file: Path, *, target: str = "3.8", log_level: str = "INFO"):  # pragma: no cover
    """
    Transfer all python files in src_dir to build_dir, and watch for changes.
    """
    assert target == "3.8", "PyFuture is very early stage, not support target argument yet"
    init_logger(log_level)
    transfer_file(src_file, tgt_file)

    from watchfiles import Change, watch

    for changes in watch(src_file):
        for mode, path in changes:
            match mode:
                case Change.modified:
                    logger.info("Source file has been modified")
                    transfer_file(Path(path), tgt_file)
                case Change.deleted:
                    logger.info("Source file has been deleted")
                    break


@app.command()
def transfer_dir(src_dir: Path, build_dir: Path, *, target: str = "3.8", log_level: str = "INFO"):
    """
    Transfer all python files in src_dir to build_dir.
    """
    assert target == "3.8", "PyFuture is very early stage, not support target argument yet"
    init_logger(log_level)

    for src_file in src_dir.glob("**/*.py"):
        tgt_file = build_dir / src_file.relative_to(src_dir)
        transfer_file(src_file, tgt_file)


@app.command()
def watch_dir(src_dir: Path, build_dir: Path, *, target: str = "3.8", log_level: str = "INFO"):  # pragma: no cover
    """
    Transfer all python files in src_dir to build_dir, and watch for changes.
    """
    assert target == "3.8", "PyFuture is very early stage, not support target argument yet"
    init_logger(log_level)
    transfer_dir(src_dir, build_dir, target=target)

    from watchfiles import Change, PythonFilter, watch

    for changes in watch(src_dir, watch_filter=PythonFilter()):
        for mode, path in changes:
            match mode:
                case Change.added | Change.modified:
                    logger.info(f"Created: {path}")
                    tgt_file = build_dir / Path(path).relative_to(src_dir)
                    transfer_file(Path(path), tgt_file)
                case Change.deleted:
                    logger.info(f"Deleted: {path}")
                    tgt_file = build_dir / Path(path).relative_to(src_dir)
                    tgt_file.unlink()


if __name__ == "__main__":  # pragma: no cover
    app()
