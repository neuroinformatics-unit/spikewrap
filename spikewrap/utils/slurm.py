import datetime
import subprocess
from pathlib import Path
from typing import Callable, Dict, Literal, Union

import submitit

from . import utils


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
    slurm_opts = kwargs.pop("slurm_batch")
    executor = get_executor(kwargs)

    job = executor.submit(
        wrap_function_with_env_setup, command_func, slurm_opts, **kwargs
    )

    if isinstance(slurm_opts, dict) and "wait" in slurm_opts and slurm_opts["wait"]:
        job.wait()

    send_user_start_message(command_name, job, kwargs)


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


def get_executor(kwargs: Dict) -> submitit.AutoExecutor:
    """
    Return the executor object that defines parameters
    of the SLURM node to request and the path to
    logs.

    Parameters
    ----------
    kwargs : Dict
        Keyword arguments passed to the main running function
        (e.g. run_full_pipeline, run_sorting).

    Returns
    -------
    executor : submitit.AutoExecutor
        submitit executor object defining requested SLURM
        node parameters.
    """
    log_path = make_job_log_output_path(kwargs)

    print(f"\nThe SLURM batch output logs will " f"be saved to {log_path}\n")

    executor = submitit.AutoExecutor(
        folder=log_path,
    )

    executor.update_parameters(
        nodes=1,
        mem_gb=40,
        timeout_min=24 * 60,
        cpus_per_task=8,
        tasks_per_node=1,
        gpus_per_node=1,
        slurm_gres="gpu:1",
        slurm_partition="gpu",
    )

    return executor


def wrap_function_with_env_setup(
    function: Callable, slurm_opts: Union[Literal[True], Dict], **kwargs
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

    kwargs : Dict
        Keyword arguments passed to the main running function
        (e.g. run_full_pipeline, run_sorting)
    """
    if isinstance(slurm_opts, dict) and "env_name" in slurm_opts:
        env_name = slurm_opts["env_name"]
    else:
        env_name = "spikewrap"

    print(f"\nrunning {function.__name__} with SLURM....\n")

    subprocess.run(
        f"module load miniconda; " f"source activate {env_name};" f"module load cuda",
        executable="/bin/bash",
        shell=True,
    )

    function(**kwargs)


def make_job_log_output_path(kwargs: Dict) -> Path:
    """
    The SLURM job logs are saved to a folder 'slurm_logs' in the
    base directory in which the processing is being run
    (i.e. the folder containing rawdata, derivatives). .

    Parameters
    ----------
    kwargs : Dict
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

    if "base_path" in kwargs:
        log_path = kwargs["base_path"] / log_subpath
    else:
        log_path = kwargs["preprocess_data"].base_path / log_subpath  # TODO: jenky

    log_path.mkdir(exist_ok=True, parents=True)

    return log_path


def send_user_start_message(
    processing_function: str, job: submitit.Job, kwargs: Dict
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

    kwargs : Dict
        Keyword arguments passed to the main running function
        (e.g. run_full_pipeline, run_sorting)
    """
    utils.message_user(
        f"{processing_function} submitted to SLURM with job id {job.job_id}\n"
        f"with arguments{kwargs}"
    )


def is_slurm_installed():
    slurm_installed = subprocess.run("sinfo -v", shell=True).returncode == 0
    return slurm_installed
