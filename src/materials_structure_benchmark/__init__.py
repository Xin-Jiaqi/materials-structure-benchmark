"""Query helpers for the Materials Structure Benchmark catalog."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("materials-structure-benchmark")
except PackageNotFoundError:  # Source checkout without an editable install.
    __version__ = "0.2.1"

__all__ = ["__version__"]
