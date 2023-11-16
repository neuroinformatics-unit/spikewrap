from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("swc_epys")
except PackageNotFoundError:
    # package is not installed
    pass

from .pipeline.full_pipeline import run_full_pipeline_wrapper
from .pipeline.preprocess import run_preprocess
from .pipeline.sort import run_sorting_wrapper
from .pipeline.postprocess import run_postprocess

from .utils.checks import check_environment
from .utils.slurm import run_interactive_slurm

__all__ = [
    "run_full_pipeline_wrapper",
    "run_preprocess",
    "run_sorting_wrapper",
    "run_postprocess",
    "check_environment",
    "run_interactive_slurm",
]
