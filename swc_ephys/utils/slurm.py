import datetime
import subprocess
from pathlib import Path

import submitit

from . import utils


def get_executor(kwargs):
    """ """
    now = datetime.datetime.now()
    log_subpath = Path("slurm_logs") / f"{now.strftime('%Y-%m-%d_%H-%M-%S')}"  # weird : formats weirdly
    if "base_path" in kwargs:
        log_path = kwargs["base_path"] / log_subpath
    else:
        log_path = kwargs["data"].base_path / log_subpath
    log_path.mkdir(exist_ok=True, parents=True)

    print(log_path)

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


def wrap_function_with_env_setup(function, slurm_opts, **kwargs):
    if isinstance(slurm_opts, dict):
        env_name = slurm_opts["env_name"]
    else:
        env_name = "swc_ephys"

    print(f"\nrunning {function.__name__} with SLURM....\n")

    subprocess.run(
        "module load miniconda", executable="/bin/bash", shell=True
    )  # TODO: make one command
    subprocess.run(
        f"source activate {env_name}", executable="/bin/bash", shell=True
    )  # TODO: make this a HPC module
    subprocess.run(
        "module load cuda", executable="/bin/bash", shell=True
    )  # TODO: probably a better way, contact IT

    function(**kwargs)


def send_user_start_message(command, job, kwargs):
    utils.message_user(
        f"{command} submitted to SLURM with job id {job.job_id}\n"
        f"with arguments{kwargs}"
    )


def run_full_pipeline_slurm(**kwargs):
    from ..pipeline.full_pipeline import run_full_pipeline

    slurm_opts = kwargs.pop("slurm_batch")
    executor = get_executor(kwargs)
    job = executor.submit(
        wrap_function_with_env_setup, run_full_pipeline, slurm_opts, **kwargs
    )
    send_user_start_message("Full pipeline", job, kwargs)


def run_sorting_slurm(**kwargs):
    from ..pipeline.sort import run_sorting

    slurm_opts = kwargs.pop("slurm_batch")
    executor = get_executor(kwargs)
    job = executor.submit(
        wrap_function_with_env_setup, run_sorting, slurm_opts, **kwargs
    )
    send_user_start_message("Sorting", job, kwargs)
