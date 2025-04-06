from __future__ import annotations

import os
from typing import Literal


def default_slurm_options(partition: Literal["cpu", "gpu"] = "cpu") -> dict:
    """
    Get a set of default SLURM job submission options based on the selected partition.

    All arguments correspond to sbatch arguments except for:

    ``wait``
        Whether to block the execution of the calling process until the job completes.

    ``env_name``
        The name of the Conda environment to run the job in. Defaults to the
        active Conda environment of the calling process, or "spikewrap" if none is detected.
        To modify this, update the returned dictionary directly.

    Parameters
    ----------
    partition
        The SLURM partition to use.

    Returns
    -------
    options
        Dictionary of SLURM job settings, including:
            nodes - The number of nodes to allocate for the job.
            mem_gb - The amount of memory (in gigabytes) to allocate per node for the job.
            timeout_min - The maximum runtime in minutes before the job is terminated.
            cpus_per_task - The number of CPUs allocated per task.
            tasks_per_node - The number of tasks to run on each node.
            slurm_partition - The SLURM partition (queue) to submit the job to.
            slurm_gres - The generic resources (e.g., GPUs) to allocate for the job, specified in the format required by SLURM.
            exclude - A list of nodes to exclude from the job allocation.
            wait - if ``True``, freeze execution until slurm job is finished.
            env_name - The name of the environment (e.g., conda or virtualenv) to activate before running the job.

    """
    env_name = os.environ.get("CONDA_DEFAULT_ENV")

    if env_name is None:
        env_name = "spikewrap"

    options = {
        "nodes": 1,
        "mem_gb": 40,
        "timeout_min": 24 * 60,
        "cpus_per_task": 8,
        "tasks_per_node": 1,
        "wait": False,
        "env_name": env_name,
    }

    if partition == "cpu":
        options.update({"slurm_partition": "cpu"})

    else:
        options.update(
            {
                "slurm_partition": "gpu",
                "slurm_gres": "gpu:1",
                "exclude": "",
            }
        )

    return options
