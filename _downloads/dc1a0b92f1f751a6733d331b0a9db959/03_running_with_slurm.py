# ruff: noqa: E402
"""
.. _slurm-tutorial:

Running with SLURM
==================

.. note::
    This is a long-form tutorial on SLURM. See :ref:`here <slurm-howto>` for a quick how-to.

What is SLURM?
--------------

SLURM is a job-manager used in high-performance computing (HPC) systems).
Its purpose is to ensure the resources of the HPC are distributed fairly
between users. 

Users 'request' resource from SLURM to run their jobs, and are allocated
the resources in a priority order calculated by SLURM.

Why use SLURM?
-------------------------------

SLURM can be used to run jobs at certain computationally-heavy steps
in the preprocessing pipeline.

In `SpikeInterface <https://spikeinterface.readthedocs.io/en/stable/>`_,
data loading and preprocessing is 'lazy', meaning operations are only
performed on data as they are needed. This makes certain operations very fast,
such as:

.. code-block::

    session.preprocess(...)
    session.plot_preprocessed(time_range=(0, 1), ...)

Only the 1 second of data that is visualized is actually preprocessed.

However, other operations will preprocess the entire dataset, like
:func:`spikewrap.Session.save_preprocessed` and sorting.

Because such steps are computationally intensive, SLURM can be used to request
dedicated resources to run the job on. It will then run in the background, allowing you
to do other things, as well as run multiple jobs at once in parallel.

"""

# %%
# Running a process with SLURM
# ----------------------------
#
# In ``spikewrap``, methods which are computationally intensive admit a ``slurm`` argument
# (currently only :func:`spikewrap.Session.save_preprocessed`).
#
# .. attention::
#     Jobs are requested at the **run level**. For example, if a
#     session has 2 runs (which are not concatenated),
#     :func:`spikewrap.Session.save_preprocessed` will request two nodes.
#
# The ``slurm`` argument can take one of three possible inputs:
#
# ``False``:
#   Do not run the job with SLURM.
# ``True``:
#   Run in SLURM with a set of default parameters (explained below)
# ``dict``:
#   Run in SLURM, passing the given job parameters in the dictionary to SLURM.
#
#   The arguments passed to SLURM tell it what kind of resources
#   you want to request. These are usually passed in an script using `sbatch <https://slurm.schedmd.com/sbatch.html>`_.
#   In ``spikewrap``, `submitit <https://github.com/facebookincubator/submitit>`_
#   is used under the hood to submit SLURM jobs with ``sbatch``.
#
#
# In ``spikewrap``, when ``slurm=True`` a set of default arguments are used.
# These can be inspected with:

import spikewrap as sw
import json

default_arguments = sw.default_slurm_options()

print(
    json.dumps(default_arguments, indent=4)  # json just for visualising output
)

# %%
# By default, these return arguments to request a CPU node.
#
# .. note::
#     Typically, HPC systems are
#     organised into a set of 'nodes' that contain isolated compute resources.
#     Nodes are requested to run jobs on. These nodes may have CPU only, or a GPU
#     (which are required by some sorters, e.g. kilosort1-3).
#
#
# .. warning::
#
#    These default arguments have been set up for the HPC system at the `Sainsbury Wellcome Center <https://www.sainsburywellcome.org/web/>`_.
#    They may not all translate to other HPC systems (e.g. partition names, nodes to exclude, use of conda).
#    Please replace settings as required.
#
# Two of the default settings do not directly correspond to ``sbatch`` arguments:
#
# ``wait``:
#    If ``True``, the job will block the executing process until the job is complete.
#
# ``env_name``:
#     The conda environment in which to execute the job. By default, this will
#     read the name of the envionrment in which the script is run (from ``os.environ.get("CONDA_DEFAULT_ENV")``
#     and if not found, set to ``"spikewrap"``.
#     To use a different environment name, edit the options as shown below.
#
#
# You can edit these arguments before passing to the ``slurm`` argument:

gpu_arguments = sw.default_slurm_options("gpu")

gpu_arguments["mem_gb"] = 60
gpu_arguments["env_name"] = "my_conda_environment"

print(
    json.dumps(gpu_arguments, indent=4)
)

# %%
# and then use like:
#
# .. code-block::
#
#   session.save_preprocessed(n_jobs=12, slurm=gpu_arguments)
#
# .. admonition:: Multiprocessing in SLURM
#    :class: warning
#
#    :func:`spikewrap.Session.save_preprocessed` takes an ``n_jobs`` argument as well
#    as the ``slurm`` argument. When are using multiple cores (``n_jobs > 1``)  it is important
#    to check you have requested at least as many cpu cores as you set with ``n_jobs``.
#
#    When the SLURM job starts, ``n_jobs`` cores.  If these are not requested and available on the node,
#    the job may run slower that it should.
#
#    **Note:** ``n_jobs`` here refers to cores for correspondance with SpikeInterface terminology.
#    This is not to be confused with a SLURM job.

# %%
# Checking the progress of a job
# ------------------------------
#
# Once the job has been submitted, you can track its progress
# in two ways.
#
# One is to `inspect the SLURM output files`_.
#
# The other is to use the commands:
#
# .. code-block::
#
#     squeue -u my_username
#
# To view all your current jobs and their status.
#
# .. _inspect the SLURM output files:
#
# Inspecting SLURM's output
# -------------------------
#
# As the SLURM job runs, it will output logs to a ``slurm_logs`` folder in the processed run folders.
#
# The two main log files are the ``.out`` and ``.err`` files are written to
# the run folder These refer to
# the ``stdout`` and ``stderr`` streams common across the major operating systems,
# which manage text.
#
# Ostensibly, ``stdout`` is for normal program output while and ``stderr``
# is for error messages, warnings and debugging output. However, this is not always handled
# intuitively (for example, pythons ``logging`` module will always write to ``stderr``.
# Therefore, it is important to inspect both logs while inspecting the output of the progress.
#
# The actual outputs of the processing (e.g. preprocessed binaries)
# will be written to the standard output folder as described [here]()





















