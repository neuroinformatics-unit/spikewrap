# ruff: noqa: E402
""" Overview
============
`(1 minute read)`


``spikewrap`` provides a Python interface for managing and
sharing standardized extracellular electrophysiology pipelines.

Built on `SpikeInterface <https://github.com/SpikeInterface/spikeinterface>`_,
``spikewrap`` places emphasis on delivering standardised outputs and
materials for convenient data quality checks.

.. attention::

   ``spikewrap`` is currently in a consultation stage, where feedback on the
   workflow is being actively solicited. New features—such as sorting,
   subject-level analysis, quality checks, support for more probes,
   and additional preprocessing steps—are planned for implementation soon.

   Please :ref:`get in contact <community>` with feedback and suggestions!

Running ``spikewrap``
---------------------

``spikewrap`` expects a project to be organised either in
`NeuroBlueprint <https://neuroblueprint.neuroinformatics.dev/latest/index.html>`_
format (which is :ref:`recommended <neuroblueprint-recommended>`), for example:

.. tab-set::
    :sync-group: category

    .. tab-item:: SpikeGLX

        .. code-block::

            └── rawdata/
                └── sub-001_.../
                    └── ses-001_.../
                        └── ephys/
                            ├── run-001_g0_imec0/
                            │   ├── run-001_g0_t0.imec0.ap.bin
                            │   └── run-001_g0_t0.imec0.ap.meta
                            └── run-002_g0_imec0/
                            │   ├── ...
                            └── ...

    .. tab-item:: OpenEphys

        .. code-block::

            └── rawdata/
                └── sub-001_.../
                    └── ses-001_.../
                        └── ephys/
                            └── Recording Node <ID>/
                                └── experiment1/
                                    ├── recording1/
                                    │   └── ...
                                    └── recording2/
                                    │   └── ...
                                    └── ...

or in custom formats with subject, session and recording folder levels as below:

.. dropdown:: Supported Custom Organisation

    .. tab-set::
        :sync-group: category

        .. tab-item:: SpikeGLX

            .. code-block::

                └── root_folder>/
                    └── my_subject_name/
                        └── my_session_name/
                            ├── run-001_g0_imec0/
                            │   ├── run-001_g0_t0.imec0.ap.bin
                            │   └── run-001_g0_t0.imec0.ap.meta
                            └── run-002_g0_imec0/
                            │   ├── ...
                            └── ...

        .. tab-item:: OpenEphys

            In the OpenEphys case, the input data would look like:

            .. code-block::

                └── root_folder/
                    └── my_subject_name/
                        └── my_session_name/
                            └── Recording Node <ID>/
                                └── experiment1/
                                    ├── recording1/
                                    │   └── ...
                                    └── recording2/
                                    │   └── ...
                                    └── ...

`SpikeGlx <https://billkarsh.github.io/SpikeGLX/>`_ or `OpenEphys <https://open-ephys.org/>`_
systems with `Neuropixels <https://www.neuropixels.org/>`_ probes are currently supported
(see :ref:`Supported Formats <supported-formats>` for details).

We can preprocess, visualise and save a recording session with a few function calls:
"""

import spikewrap as sw

subject_path = sw.get_example_data_path() / "rawdata" / "sub-001"

session = sw.Session(
    subject_path=subject_path,
    session_name="ses-001",
    run_names="all",
    file_format="spikeglx"  # or "openephys"
)

# Run (lazy) preprocessing, for fast plotting
# and prototyping of preprocessing steps

session.preprocess(
    configs="neuropixels+kilosort2_5",
    per_shank=True,
    concat_runs=False,
)

plots = session.plot_preprocessed(
    run_idx=0,
    time_range=(0, 0.5),
    show_channel_ids=False,
    show=True
)

# Write preprocessed data to disk, optionally
# in a SLURM job (if on a HPC)

session.save_preprocessed(
    overwrite=True,
    n_jobs=12,
    slurm=False
)

# %%
# with data output to the standardised
# `NeuroBlueprint <https://neuroblueprint.neuroinformatics.dev/latest/index.html>`_
# structure:
#
# .. code-block::
#
#    └── root_folder/
#        └── derivatives/
#            └── sub-001/
#                └── ses-001  /
#                    └── ephys/
#                        └── run-001_g0_imec0/
#                        │   ├── preprocessed/
#                        │   │   ├── shank_0/
#                        │   │   │   └── si_recording/
#                        │   │   │       └── <spikeinterface binary>
#                        │   │   └── shank_1/
#                        │   │       └── si_recording/
#                        │   │           └── <spikeinterface binary>
#                        │   └── sync/
#                        │       └── sync_channel.npy
#                        └── run-002_g0_imec0/
#                            └── ...
#
# Next, visit :ref:`get-started` and :ref:`tutorials_index` to try out ``spikewrap``.
