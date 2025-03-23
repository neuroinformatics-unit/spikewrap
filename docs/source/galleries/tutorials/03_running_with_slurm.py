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

Users request resources from SLURM to run their jobs, and are allocated
the resources in a priority order calculated by SLURM.

Why use SLURM?
--------------

SLURM can be used to run jobs at certain computationally-heavy steps
in the preprocessing pipeline.

In `SpikeInterface <https://spikeinterface.readthedocs.io/en/stable/>`_,
data loading and many preprocessing steps are 'lazy', meaning operations are only
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
# Running a single function with SLURM
# ------------------------------------
#
# In ``spikewrap``, methods which are computationally intensive admit a ``slurm`` argument
# When set, the function will be run within a SLURM job:
#
# .. code-block:: python
#
#     import spikewrap as sw
#
#     session = sw.Session(
#         subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
#         session_name="ses-001",
#         file_format="spikeglx",
#         run_names="all"
#     )
#
#     session.preprocess(configs="neuropixels+kilosort2_5")
#
#     session.save_preprocessed(slurm=True)
#
# The ``slurm`` argument can take one of three possible inputs:
#
# ``False`` (do not run the job with SLURM), ``True`` (run in SLURM with a set of
# default parameters) or a ``dict`` of job parameters. See :ref:`configuring SLURM <configuring-slurm>`
# for more details and :ref:`SLURM logs <slurm-logs>` to keep track of running SLURM jobs.
#
# Note that jobs are requested at the **run level**. For example, if
# a session has 2 runs (which are not concatenated), :func:`spikewrap.Session.save_preprocessed`
# will request two nodes.
#
# .. warning::
#
#    Chaining functions with ``slurm=True`` can lead to out-of-order code execution.
#    For example, imagine we run sorting after saving the preprocessed data:
#
#    .. code-block :: python
#
#        session.save_preprocessed(slurm=True)
#
#        session.sort("neuropixels+kilosort2_5", slurm=True)
#
#    Here, the ``save_preprocessed`` will be triggered to be run in a separate SLURM
#    job, that will take a while to run. However, execution of the script will continue, and ``session.sort``
#    will be called immediately. As the preprocessed data will not yet be saved, and an error will be called.
#
#    See below on how to chain multiple function calls together with SLURM.
#
# Chaining SLURM commands: processing a single-run
# ------------------------------------------------
# .. _chaining-slurm:
#
# To avoid the issue with out-of-order execution described above, we
# can wrap multiple functions together and run them in a single SLURM job.
#
# We wrap functions calls in an inner function (these dont have to be
# just functions with the ``slurm`` argument, and run with the function
# :func:`spikewrap.run_in_slurm`.
#
# For example:
#
# .. code-block:: python
#
#     def capture_for_slurm():
#
#         session = sw.Session(
#             subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
#             session_name="ses-001",
#             file_format="spikeglx",
#             run_names="run-001
#         )
#
#         session.preprocess(configs="neuropixels+kilosort2_5")
#
#         # We want to set `slurm=False` here, otherwise our SLURM jobs
#         # will spawn more SLURM jobs!
#
#         session.save_preprocessed(slurm=False)
#
#         session.sort("neuropixels+kilosort2_5", slurm=False)
#
#     sw.run_in_slurm(
#         slurm_opts=None,
#         func_to_run=capture_for_slurm,
#         log_base_path=session.get_output_path()
#
# Where ``slurm_opts`` are the slurm options :ref:`below <chaining-slurm>`),
# ``func_to_run`` is the function to run in slurm, and ``log_base_path``
# is where the slurm logs will be saved (we set to the session output path).

# %%
# Chaining SLURM commands: processing multiple runs
# -------------------------------------------------
#
# When we have multiple runs, the above approach may not be ideal.
# For example, imagine we have three runs associated with a session:
#
# .. code-block:: python
#
#     def capture_for_slurm():
#
#         session = sw.Session(
#             subject_path="/path/to/sub,
#             session_name="ses-001",
#             file_format="spikeglx",
#             run_names=["run-001, "run-002", "run-003"]
#         )
#
#         session.preprocess(configs="neuropixels+kilosort2_5")
#
#         session.save_preprocessed(slurm=False)
#
#         session.wait_for_slurm()  # this will wait until all running SLURM jobs are finished
#
#         session.sort("neuropixels+kilosort2_5", concat_runs=True, slurm=False)
#
# Now ``session.save_preprocessed(slurm=False)`` will freeze execution
# while all runs are saved sequentially, thanks to :func:`spikewrap.Session.wait_for_slurm`.
# Then, it will move on to sorting, which will be run sequentially.
# Therefore, processing the runs will not be parallelized.
#
# Instead, we can set ``slurm=True`` on ``save_preprocessed`` above. In this case, execution
# of ``save_preprocessed`` will spawn three slurm jobs (one per run). Then the process
# will wait until all three jobs have completed. Once completed, sorting will be run,
# first concatenating the saved preprocessed recordings together. We do not need to run
# that job in SLURM, because there is only one run (as data is concatenated).
#
# We can even run this entire job in SLURM, and from that job spawn more slurm jobs
# to take advantage of parallelization of saving the preprocessing. This means we don't have
# to use the current process, which may be killed if the connection to the HPC is lost. For example:
#
# .. code-block:: python
#
#  def capture_for_slurm():
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
#  sw.run_in_slurm(
#      slurm_opts=None,
#      func_to_run=capture_for_slurm,
#      log_base_path=session.get_output_path()
#  )
#
# In the above example, the captured functions will be run in a SLURM job.
# Within that SLURM job, 3 more SLURM jobs will be spawned to save the
# three preprocessed runs. Then, once the 3 SLURM jobs are complete, the
# sorting will be run in the original slurm job.

# %%
# Configuring SLURM
# -----------------
# .. _configuring-slurm:
#
# In ``spikewrap``, when ``slurm=True`` a set of default arguments are used.
#
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
#    **Note:** ``n_jobs`` here refers to cores for correspondence with SpikeInterface terminology.
#    This is not to be confused with a SLURM job.
#

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
# .. _slurm-logs:
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




















