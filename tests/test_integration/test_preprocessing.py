from __future__ import annotations

import numpy as np
import pytest
import spikeinterface.full as si
from base import BaseTest

import spikewrap as sw


class TestPreprocessing(BaseTest):

    # TODO: this fixture is almost a direct copy, align across tests
    @pytest.fixture(scope="function")
    def session(self, tmp_path):
        session = sw.Session(
            subject_path=sw.get_example_data_path("spikeglx") / "rawdata" / "sub-001",
            session_name="ses-001",
            file_format="spikeglx",
            run_names="all",
            output_path=tmp_path,
        )

        # no need to tear down as each run is in a new `tmp_path`
        return session

    # TODO: get raw runs
    # TODO: get preprocessed runs
    # TODO: make sure docs are clear on the "1"
    # TOOD: we are no longer lazy!
    # TODO: this test is slow! maybe use a fake recording that is extremely short...?
    def test_remove_bad_channels(self, session):
        """ """
        detect_bad_channel_kwargs = {
            "dead_channel_threshold": -0.1,
            "welch_window_ms": 1.0,
            "seed": 42,
        }
        pp_steps = {
            "1": [
                "remove_bad_channels",
                {"detect_bad_channel_kwargs": detect_bad_channel_kwargs},
            ]
        }

        session.preprocess(pp_steps, concat_runs=False, per_shank=False)

        for run_idx in [0, 1]:

            bad_channel_ids, _ = si.detect_bad_channels(
                session._raw_runs[run_idx]._raw["grouped"], **detect_bad_channel_kwargs
            )
            check_removed_recording = (
                session._raw_runs[run_idx]
                ._raw["grouped"]
                .remove_channels(bad_channel_ids)
            )

            pp_recording = session._pp_runs[run_idx]._preprocessed["grouped"][
                "1-raw-remove_bad_channels"
            ]

            assert (
                pp_recording.get_num_channels() < 384
            ), "somehow channels were not removed in the test environment."
            assert np.array_equal(
                check_removed_recording.get_traces(), pp_recording.get_traces()
            )
            assert all(
                check_removed_recording.get_channel_ids()
                == pp_recording.get_channel_ids()
            )

        # TODO: write a doc on working with concatenated recordings, actually need to
        # investigate this properly in the CatGT case especially but also openEphys
        session.preprocess(pp_steps, concat_runs=True)
        concat_runs = si.concatenate_recordings(
            [run._raw["grouped"] for run in session._raw_runs]
        )
        bad_channel_ids, _ = si.detect_bad_channels(
            concat_runs, **detect_bad_channel_kwargs
        )
        check_removed_recording = concat_runs.remove_channels(bad_channel_ids)

        pp_recording = session._pp_runs[0]._preprocessed["grouped"][
            "1-raw-remove_bad_channels"
        ]

        assert (
            pp_recording.get_num_channels() < 384
        ), "somehow channels were not removed in the test environment."
        assert np.array_equal(
            check_removed_recording.get_traces(), pp_recording.get_traces()
        )
        assert all(
            check_removed_recording.get_channel_ids() == pp_recording.get_channel_ids()
        )

        # Now split by shank and check the last shank is correct
        session.preprocess(pp_steps, concat_runs=False, per_shank=True)

        last_shank = session._raw_runs[1]._raw["grouped"].split_by("group")[1]

        bad_channel_ids, _ = si.detect_bad_channels(
            last_shank, **detect_bad_channel_kwargs
        )
        check_removed_recording = last_shank.remove_channels(bad_channel_ids)

        pp_recording = session._pp_runs[1]._preprocessed["shank_1"][
            "1-raw-remove_bad_channels"
        ]

        assert (
            pp_recording.get_num_channels() < 384
        ), "somehow channels were not removed in the test environment."
        assert np.array_equal(
            check_removed_recording.get_traces(), pp_recording.get_traces()
        )
        assert all(
            check_removed_recording.get_channel_ids() == pp_recording.get_channel_ids()
        )

    # TODO
    # test interpolate
    # note remove_channels and interpolate_channels are implicitly tested by these tests as are used under the hood
    # but should probably jsut test anyways to be clear, it will be fast

    def test_interpolate_bad_channels(self):
        pass
