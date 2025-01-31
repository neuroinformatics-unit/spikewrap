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
        Dictionary of SLURM job settings.
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
                "exclude": "gpu-sr670-20,gpu-sr670-21,gpu-sr670-22",
            }
        )

    return options
