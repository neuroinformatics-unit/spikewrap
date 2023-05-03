import datetime
import subprocess
from pathlib import Path
from typing import Callable, Dict

import submitit

from . import utils


def get_executor(kwargs: Dict) -> submitit.AutoExecutor:
    """ """
    log_path = make_job_log_output_path(kwargs)

    print(f"\nThe SLURM batch output logs will be saved to {log_path}\n")

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
    function: Callable, slurm_opts: Dict, **kwargs
) -> None:
    """ """
    if isinstance(slurm_opts, dict):
        env_name = slurm_opts["env_name"]
    else:
        env_name = "swc_ephys"

    print(f"\nrunning {function.__name__} with SLURM....\n")

    subprocess.run(
        f"module load miniconda; " f"source activate {env_name};" f"module load cuda",
        executable="/bin/bash",
        shell=True,
    )

    function(**kwargs)


def send_user_start_message(command: str, job: submitit.Job, kwargs: Dict) -> None:
    """ """
    utils.message_user(
        f"{command} submitted to SLURM with job id {job.job_id}\n"
        f"with arguments{kwargs}"
    )


def run_full_pipeline_slurm(**kwargs) -> None:
    """ """
    from ..pipeline.full_pipeline import run_full_pipeline

    slurm_opts = kwargs.pop("slurm_batch")
    executor = get_executor(kwargs)
    job = executor.submit(
        wrap_function_with_env_setup, run_full_pipeline, slurm_opts, **kwargs
    )
    send_user_start_message("Full pipeline", job, kwargs)


def run_sorting_slurm(**kwargs) -> None:
    """ """
    from ..pipeline.sort import run_sorting

    slurm_opts = kwargs.pop("slurm_batch")
    executor = get_executor(kwargs)
    job = executor.submit(
        wrap_function_with_env_setup, run_sorting, slurm_opts, **kwargs
    )
    send_user_start_message("Sorting", job, kwargs)


def make_job_log_output_path(kwargs: Dict) -> Path:
    """ """
    now = datetime.datetime.now()

    log_subpath = Path("slurm_logs") / f"{now.strftime('%Y-%m-%d_%H-%M-%S')}"

    if "base_path" in kwargs:
        log_path = kwargs["base_path"] / log_subpath
    else:
        log_path = kwargs["data"].base_path / log_subpath

    log_path.mkdir(exist_ok=True, parents=True)

    return log_path
