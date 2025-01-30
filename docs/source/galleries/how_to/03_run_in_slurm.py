# ruff: noqa: E402
"""
.. _slurm-howto:

How to run in SLURM
===================

.. note::
    This is a quick how-to on SLURM. See :ref:`here <slurm-tutorial>` for a long-form tutorial.

"""

# %%
# See the default SLURM options, used when ``slurm=True``

import spikewrap as sw
import json

default_arguments = sw.default_slurm_options()

print(
    json.dumps(default_arguments, indent=4)  # json just for visualising output
)


# %%
# Otherwise, we can update these as desired:

gpu_arguments = sw.default_slurm_options("gpu")

gpu_arguments["mem_gb"] = 60
gpu_arguments["env_name"] = "my_conda_environment"

print(
    json.dumps(gpu_arguments, indent=4)
)

# and then use like:
# session.save_preprocessed(n_jobs=12, slurm=gpu_arguments)
