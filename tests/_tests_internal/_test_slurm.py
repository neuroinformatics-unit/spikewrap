from __future__ import annotations

import shutil

import numpy as np
import pytest
import spikeinterface.full as si

import spikewrap as sw

# IN PROGRESS
# TODO
# 1) add docstrings to all tests
# 2) perform an assert in `test_slurm_sync`
# 3) Only preprocessing performs an equality test, all other
#    tests just check it ran successfully. Extend equality checks
#    to all other tests.


class TestSlurmInternal:

    @pytest.fixture(scope="function")
    def teardown_derivatives_fixture(self):

        derivatives_path = sw.get_example_data_path() / "derivatives"

        if derivatives_path.is_dir():
            shutil.rmtree(derivatives_path)

        yield

    def test_slurm_sync(self, teardown_derivatives_fixture):
        """ """
        session = sw.Session(
            subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
            session_name="ses-001",
            file_format="spikeglx",
        )

        session.load_raw_data()

        slurm_opts = sw.default_slurm_options("cpu")
        slurm_opts["wait"] = True

        session.save_sync_channel(slurm=slurm_opts)

    def test_slurm_prepro(self, teardown_derivatives_fixture):
        """ """
        session = sw.Session(
            subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
            session_name="ses-001",
            file_format="spikeglx",
        )
        session.preprocess(
            configs="neuropixels+kilosort2_5", per_shank=False, concat_runs=False
        )

        slurm_opts = sw.default_slurm_options("cpu")
        slurm_opts["wait"] = True
        session.save_preprocessed(overwrite=True, n_jobs=6, slurm=slurm_opts)

        for run_idx in range(2):

            run_path = session.get_output_path() / session.get_raw_run_names()[run_idx]

            out_path_run = si.load_extractor(run_path / "preprocessed")

            assert np.array_equal(
                out_path_run.get_traces(),
                session._pp_runs[run_idx]
                ._preprocessed["grouped"][
                    "3-raw-phase_shift-bandpass_filter-common_reference"
                ]
                .get_traces(),
            )

            slurm_folder = list((run_path.parent / "slurm_logs").glob("*"))[-1]
            slurm_file = list(slurm_folder.glob("*.out"))[0]

            with open(slurm_file, "r") as file:
                content = file.read()

            assert "Exiting after successful completion" in content

    def test_slurm_sort(self, teardown_derivatives_fixture):
        """"""
        session = sw.Session(
            subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
            session_name="ses-001",
            file_format="spikeglx",
        )
        session.preprocess(
            configs="neuropixels+mountainsort5", per_shank=False, concat_runs=False
        )

        slurm_opts = sw.default_slurm_options("cpu")
        slurm_opts["wait"] = True

        config_dict = sw.load_config_dict(
            sw.get_configs_path() / "neuropixels+mountainsort5.yaml"
        )
        config_dict["sorting"]["mountainsort5"] = {"whiten": False}

        session.sort(configs=config_dict, overwrite=True, slurm=slurm_opts)

        # Check output exists.
        for run_idx in range(2):
            assert (
                session._sorting_runs[run_idx]._output_path
                / "sorter_output"
                / "firings.npz"
            ).is_file()

    def test_run_double_job_in_slurm(self, teardown_derivatives_fixture):
        """"""
        session = sw.Session(
            subject_path=sw.get_example_data_path() / "rawdata" / "sub-001",
            session_name="ses-001",
            file_format="spikeglx",
        )

        def wrap_for_slurm():
            session.preprocess(
                configs="neuropixels+mountainsort5", per_shank=False, concat_runs=False
            )

            session.save_preprocessed(overwrite=True, n_jobs=6, slurm=False)

            session.sort(
                configs="neuropixels+mountainsort5", overwrite=True, slurm=False
            )

        slurm_opts = sw.default_slurm_options("cpu")
        slurm_opts["wait"] = True

        sw.run_in_slurm(slurm_opts, wrap_for_slurm, session.get_output_path())

        # Check output exists.
        session.load_raw_data()

        assert (
            session.get_output_path() / session.get_raw_run_names()[0] / "sorting"
        ).is_dir()

        assert (
            session.get_output_path() / session.get_raw_run_names()[0] / "preprocessed"
        ).is_dir()
