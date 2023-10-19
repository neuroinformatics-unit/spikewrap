from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("spikewrap")
except PackageNotFoundError:
    # package is not installed
    pass

from .pipeline.full_pipeline import run_full_pipeline
from .pipeline.preprocess import run_preprocess
from .pipeline.sort import run_sorting
from .pipeline.postprocess import run_postprocess

from .utils.checks import check_environment
from .utils.slurm import run_interactive_slurm

__all__ = [
    "run_full_pipeline",
    "run_preprocess",
    "run_sorting",
    "run_postprocess",
    "check_environment",
    "run_interactive_slurm",
]
