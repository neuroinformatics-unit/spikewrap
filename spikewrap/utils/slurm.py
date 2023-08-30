import datetime
import subprocess
from pathlib import Path
from typing import Callable, Dict

import submitit

from ..configs.backend.hpc import (
    default_cpu_partition,
    default_gpu_partition,
    default_slurm_options,
)
from . import utils
from .checks import system_call_success


def run_job(kwargs, command_func: Callable, command_name: str) -> None:
    """
    Run a job (e.g. run_full_pipeline, run_sorting) on SLURM.

    Parameters
    ----------
    kwargs : Dict
        Keyword arguments passed to run_full_pipeline.

    command_func : Callable
        The function to run (e.g. `run_full_pipeline()`.

    command_name : str
        The name of the command, typically command_func.__name__,
        formatted for logging.
    """
    passed_slurm_opts = kwargs.pop("slurm_batch")
    func_opts = kwargs

    slurm_opts = default_slurm_options()

    if isinstance(passed_slurm_opts, Dict):
        slurm_opts.update(passed_slurm_opts)

    should_wait = slurm_opts.pop("wait")
    env_name = slurm_opts.pop("env_name")

    executor = get_executor(func_opts, slurm_opts)

    job = executor.submit(
        wrap_function_with_env_setup, command_func, env_name, func_opts
    )

    if should_wait:
        job.wait()

    send_user_start_message(command_name, job, func_opts)


def run_full_pipeline_slurm(**kwargs) -> None:
    """
    Run the entire preprocessing pipeline in a SLURM job.

    This takes the kwargs passed to the original call of the
    preprocessing function, and feeds them back to the function
    from within the SLURM job.

    Parameters
    ----------
    kwargs : Dict
        Keyword arguments passed to run_full_pipeline.

    Notes
    -----
    The import must occur here to avoid recursive imports.
    """
    from ..pipeline.full_pipeline import run_full_pipeline

    run_job(kwargs, run_full_pipeline, "Full pipeline")


def run_sorting_slurm(**kwargs) -> None:
    """
    Run the sorting pipeline from within a SLURM job.

    See run_full_pipeline_slurm for details, this is identical
    except it is for run_sorting rather than run_full_pipeline.

    Notes
    -----
    The import must occur here to avoid recursive imports.
    """
    from ..pipeline.sort import run_sorting

    run_job(kwargs, run_sorting, "Sorting")


def run_preprocessing_slurm(**kwargs) -> None:
    """ """
    from ..pipeline.preprocess import run_preprocess

    run_job(kwargs, run_preprocess, "Preprocessing")


# Utils --------------------------------------------------------------------------------


def get_executor(func_opts: Dict, slurm_opts: Dict) -> submitit.AutoExecutor:
    """
    Return the executor object that defines parameters
    of the SLURM node to request and the path to
    logs.

    Parameters
    ----------
    func_opts : Dict
        All arguments passed to the public function, minus
        `slurm_batch`

    slurm_opts : Dict
        The slurm options to run. This includes `spikewarp` default
        slurm options overwritten where passed by user-defined
        `slurm_batch`.

    Returns
    -------
    executor : submitit.AutoExecutor
        submitit executor object defining requested SLURM
        node parameters.
    """
    log_path = make_job_log_output_path(func_opts)

    print(f"\nThe SLURM batch output logs will " f"be saved to {log_path}\n")

    executor = submitit.AutoExecutor(
        folder=log_path,
    )

    executor.update_parameters(**slurm_opts)

    return executor


def wrap_function_with_env_setup(
    function: Callable, env_name: str, func_opts: Dict
) -> None:
    """
    Set up the environment from within the SLURM job, prior
    to running the processing function (e.g. run_full_pipeline).

    This is required to set up the conda environment within the job
    or the processing function will fail.

    Parameters
    ----------
    function : Callable
        The ephys processing function to run in the SLURM job
        e.g. run_full_pipeline, run_sorting

    slurm_opts : Union[Literal[True], Dict]
        A kwarg passed to the processing function (e.g. run_full_pipeline)
        indicating whether to run in the SLURM job. If True or a Dict,
        the SLURM job is run. If a dict, the environment setup
        can be passed in the 'env_name' field.

    func_opts : Dict
        All arguments passed to the public function, minus
        `slurm_batch`
    """
    print(f"\nrunning {function.__name__} with SLURM....\n")

    subprocess.run(
        f"module load miniconda; " f"source activate {env_name}; " f"module load cuda",
        executable="/bin/bash",
        shell=True,
    )

    function(**func_opts)


def make_job_log_output_path(func_opts: Dict) -> Path:
    """
    The SLURM job logs are saved to a folder 'slurm_logs' in the
    base directory in which the processing is being run
    (i.e. the folder containing rawdata, derivatives). .

    Parameters
    ----------
    func_opts : Dict
        Keyword arguments passed to the main running function
        (e.g. run_full_pipeline, run_sorting)

    Returns
    -------
    log_path : Path
        The path to the SLURM log output folder for the current job.
        The logs are saved to a folder with machine datetime.
    """
    now = datetime.datetime.now()

    log_subpath = Path("slurm_logs") / f"{now.strftime('%Y-%m-%d_%H-%M-%S')}"

    if "base_path" in func_opts:
        log_path = func_opts["base_path"] / log_subpath
    else:
        # in the case of `run_preprocess()`, the
        # `PreprocessingData` object is passed.
        log_path = func_opts["preprocess_data"].base_path / log_subpath

    log_path.mkdir(exist_ok=True, parents=True)

    return log_path


def send_user_start_message(
    processing_function: str, job: submitit.Job, func_opts: Dict
) -> None:
    """
    Convenience function to print important information
    regarding the SLURM job.

    Parameters
    ----------
    processing_function : str
        The function being run (i.e. run_full_pipeline, run_sorting)

    job : submitit.job
        submitit.job object holding the SLURM job_id

    func_opts : Dict
        Keyword arguments passed to the main running function
        (e.g. run_full_pipeline, run_sorting)
    """
    utils.message_user(
        f"{processing_function} submitted to SLURM with job id {job.job_id}\n"
        f"with arguments{func_opts}"
    )


def is_slurm_installed():
    slurm_installed = system_call_success("sinfo -v")
    return slurm_installed


def run_interactive_slurm(partition=None, gpu=True, mem_gb="40GB", cpus=16):
    """
    A convenience function to start an interactive SLURM session. Gives quick
    access for some basic settings - the purpose is not to provide a comprehensive
    wrapper, of course native `srun` can be called. It is only to provide a
    quick convenience wrapper to get started quick with some sensible defaults.
    """
    if not is_slurm_installed():
        raise RuntimeError(
            "Cannot setup interactive SLURM because SLURM is not "
            "installed on this machine."
        )

    if partition is None:
        partition = default_gpu_partition() if gpu else default_cpu_partition()

    gpu_opt = "--gres=gpu:1" if gpu else ""

    default_opts = default_slurm_options()
    exclude = default_opts["exclude"]

    command = f"srun -p {partition} {gpu_opt} -n {cpus} --mem={mem_gb} --exclude {exclude} --pty bash -i"

    subprocess.run(command, shell=True)
