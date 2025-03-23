# ruff: noqa: E402
"""
.. _slurm-howto:

How to run in SLURM
===================

.. note::
    This is a quick how-to on SLURM. See :ref:`here <slurm-tutorial>` for a long-form tutorial.

"""

# %%
#
# The below code will run all captured code within a single slurm job.
# From within this SLURM job, the call to ``session.save_preprocessed(slurm=True)``
# will spawn three additional SLURM jobs (parallelising across three runs).
#
# After they have finished running, sorting will be run and the SLURM job will terminate.
#
# .. code-block:: python
#
#     import spikewrap as sw
#
#     def capture_for_slurm():
#
#         session = sw.Session(
#             subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
#             session_name="ses-001",
#             file_format="spikeglx",
#             run_names=["run-001, "run-002", "run-003"]
#         )
#
#         session.preprocess(configs="neuropixels+kilosort2_5")
#
#         session.save_preprocessed(slurm=True)
#
#         session.wait_for_slurm()
#
#         session.sort("neuropixels+kilosort2_5", concat_runs=True, slurm=False)
#
#     sw.run_in_slurm(
#         slurm_opts=None,
#         func_to_run=capture_for_slurm,
#         log_base_path=session.get_output_path()
#     )

# %%
# Managing SLURM options - see the default SLURM options, used when ``slurm=True``

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
