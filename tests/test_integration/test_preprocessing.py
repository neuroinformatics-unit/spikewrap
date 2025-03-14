from __future__ import annotations

import numpy as np
import pytest
import spikeinterface.full as si
from base import BaseTest
from spikeinterface.preprocessing import interpolate_bad_channels

import spikewrap as sw
from spikewrap.process._preprocessing import _get_bad_channel_ids


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
        session.load_raw_data()
        # no need to tear down as each run is in a new `tmp_path`
        return session

    def get_bad_channel_kwargs(self):
        """
        Chosen to ensure all types of bad channel label are found.
        """
        return {
            "dead_channel_threshold": -0.1,
            "welch_window_ms": 1.0,
            "outside_channel_threshold": -0.015,
            "psd_hf_threshold": 0.01,
            "num_random_chunks": 5,
            "seed": 42,
        }

    def ids_from_channel_label(self, label, channel_ids, channel_labels):

        if label == "all":
            label = ["dead", "noise", "out"]
        elif isinstance(label, str):
            label = [label]

        all_ids = [
            id for idx, id in enumerate(channel_ids) if channel_labels[idx] in label
        ]
        return all_ids

    def test_remove_bad_channels(self, session):
        """
        Check remove bad channel implementation in spikewrap (sw)
        vs spikeinterface (si).

        Notes
        -----
        This checks across different preprocessing
        approaches (concat_run, per shank). In general this should be tested
        at a higher level otherwise these will be pointlessly duplicated across
        all tests. But as this is the first test, it makes to include here for now.
        """
        # Remove bad channels in spikewrap
        detect_bad_channel_kwargs = self.get_bad_channel_kwargs()

        pp_steps = {
            "1": [
                "remove_bad_channels",
                {"detect_bad_channel_kwargs": detect_bad_channel_kwargs},
            ]
        }

        session.preprocess(pp_steps, concat_runs=False, per_shank=False)

        # For each run, remove the bad channels in spikeinterface and check it matches.
        for run_idx in [0, 1]:

            bad_channel_ids, _ = si.detect_bad_channels(
                session._raw_runs[run_idx]._raw["grouped"], **detect_bad_channel_kwargs
            )
            si_recording = (
                session._raw_runs[run_idx]
                ._raw["grouped"]
                .remove_channels(bad_channel_ids)
            )

            sw_recording = session._pp_runs[run_idx]._preprocessed["grouped"][
                "1-raw-remove_bad_channels"
            ]

            self.check_remove_bad_channel(sw_recording, si_recording)

        # Now do the same, but with concat_runs=True

        session.preprocess(pp_steps, concat_runs=True)
        concat_runs = si.concatenate_recordings(
            [run._raw["grouped"] for run in session._raw_runs]
        )
        bad_channel_ids, _ = si.detect_bad_channels(
            concat_runs, **detect_bad_channel_kwargs
        )
        si_recording = concat_runs.remove_channels(bad_channel_ids)

        sw_recording = session._pp_runs[0]._preprocessed["grouped"][
            "1-raw-remove_bad_channels"
        ]

        self.check_remove_bad_channel(sw_recording, si_recording)

        # Now split by shank and check the last shank is correct
        session.preprocess(pp_steps, concat_runs=False, per_shank=True)

        last_shank = session._raw_runs[1]._raw["grouped"].split_by("group")[1]

        bad_channel_ids, _ = si.detect_bad_channels(
            last_shank, **detect_bad_channel_kwargs
        )
        si_recording = last_shank.remove_channels(bad_channel_ids)

        sw_recording = session._pp_runs[1]._preprocessed["shank_1"][
            "1-raw-remove_bad_channels"
        ]

        self.check_remove_bad_channel(sw_recording, si_recording)

    def check_remove_bad_channel(self, sw_recording, si_recording):
        """
        Check data matches as well as channel ID order.
        """
        assert (
            sw_recording.get_num_channels() < 384
        ), "somehow channels were not removed in the test environment."
        assert np.array_equal(sw_recording.get_traces(), si_recording.get_traces())
        assert all(sw_recording.get_channel_ids() == si_recording.get_channel_ids())

    def test_interpolate_bad_channels(self, session):
        """
        Similar to above, check that interpolate bad channels
        in spikerwap matches spikeinterface.
        """
        interpolate_bad_channel_kwargs = {"sigma_um": 0.005}
        detect_bad_channel_kwargs = self.get_bad_channel_kwargs()

        pp_steps = {
            "1": [
                "interpolate_bad_channels",
                {
                    "detect_bad_channel_kwargs": detect_bad_channel_kwargs,
                    "interpolate_bad_channel_kwargs": interpolate_bad_channel_kwargs,
                },
            ]
        }

        session.preprocess(pp_steps, concat_runs=False, per_shank=False)

        for run_idx in [0, 1]:

            raw_recording = session._raw_runs[run_idx]._raw["grouped"]

            bad_channel_ids, _ = si.detect_bad_channels(
                raw_recording, **detect_bad_channel_kwargs
            )
            check_interpolate_recording = interpolate_bad_channels(
                raw_recording, bad_channel_ids, **interpolate_bad_channel_kwargs
            )

            sw_recording = session._pp_runs[run_idx]._preprocessed["grouped"][
                "1-raw-interpolate_bad_channels"
            ]

            assert not np.array_equal(
                sw_recording, raw_recording
            ), "somehow channels were not interpolated in the test environment."
            assert np.array_equal(
                check_interpolate_recording.get_traces(), sw_recording.get_traces()
            )
            assert all(
                check_interpolate_recording.get_channel_ids()
                == sw_recording.get_channel_ids()
            )

    def test_remove_then_interpolate(self, session):
        """
        This might be a common mode, so a quick test to
        check nothing unexpected happens. Test removing
        'out' channels then interpolating 'noise' and 'dead' channels.
        """
        interpolate_bad_channel_kwargs = {"sigma_um": 0.005}
        detect_bad_channel_kwargs = self.get_bad_channel_kwargs()

        pp_steps = {
            "1": [
                "remove_bad_channels",
                {
                    "labels_to_remove": "out",
                    "detect_bad_channel_kwargs": detect_bad_channel_kwargs,
                },
            ],
            "2": [
                "interpolate_bad_channels",
                {
                    "labels_to_remove": ["noise", "dead"],
                    "detect_bad_channel_kwargs": detect_bad_channel_kwargs,
                    "interpolate_bad_channel_kwargs": interpolate_bad_channel_kwargs,
                },
            ],
        }

        # preprocess within spikewrap, first removing out channels
        # then interpolating other bad channels
        session.preprocess(pp_steps)

        raw_recording = session._raw_runs[0]._raw["grouped"]

        # First detect and remove the "out" channels in SI
        _, labels = si.detect_bad_channels(raw_recording, **detect_bad_channel_kwargs)
        out_ids = self.ids_from_channel_label(
            "out", raw_recording.get_channel_ids(), labels
        )

        out_removed_recording = raw_recording.remove_channels(out_ids)

        # Then interpolate other bad channels in SI
        _, labels = si.detect_bad_channels(
            out_removed_recording, **detect_bad_channel_kwargs
        )

        bad_ids = self.ids_from_channel_label(
            ["noise", "dead"], out_removed_recording.get_channel_ids(), labels
        )

        si_recording = si.interpolate_bad_channels(
            out_removed_recording, bad_ids, **interpolate_bad_channel_kwargs
        )

        # Test SI and SW approach match.
        sw_recording = session._pp_runs[0]._preprocessed["grouped"][
            "2-raw-remove_bad_channels-interpolate_bad_channels"
        ]

        assert np.array_equal(si_recording.get_traces(), sw_recording.get_traces())
        assert all(si_recording.get_channel_ids() == sw_recording.get_channel_ids())

    def test_remove_channels(self, session):
        """
        Quick test that 'remove_channels' removes
        the correct channel (this is also implicitly tested in
        the above tests but can't hurt to test explicitly).
        """
        raw_recording = session._raw_runs[0]._raw["grouped"]

        chan_to_remove = raw_recording.get_channel_ids()[5]  # arbitrary id

        pp_steps = {"1": ["remove_channels", {"channel_ids": [chan_to_remove]}]}

        session.preprocess(pp_steps)
        pp_recording = session._pp_runs[0]._preprocessed["grouped"][
            "1-raw-remove_channels"
        ]

        assert chan_to_remove not in pp_recording.get_channel_ids()
        assert pp_recording.get_num_channels() == raw_recording.get_num_channels() - 1

    def test_interpolate_channels(self, session):
        """
        Quick test that 'interpolate channels' interpolates
        the correct channel.
        """
        raw_recording = session._raw_runs[0]._raw["grouped"]

        chan_to_interpolate = raw_recording.get_channel_ids()[5]

        pp_steps = {
            "1": [
                "interpolate_channels",
                {
                    "channel_ids": [chan_to_interpolate],
                    "interpolate_bad_channel_kwargs": {"sigma_um": 0.1},
                },
            ]
        }

        session.preprocess(pp_steps)
        pp_recording = session._pp_runs[0]._preprocessed["grouped"][
            "1-raw-interpolate_channels"
        ]

        raw_data = raw_recording.get_traces()
        pp_data = pp_recording.get_traces()

        assert np.array_equal(raw_data[:, :5], pp_data[:, :5])
        assert not np.array_equal(raw_data[:, 5], pp_data[:, 5])
        assert np.array_equal(raw_data[:, 6:], pp_data[:, 6:])

    # TODO: see why this takes so long
    @pytest.mark.parametrize("file_format", ["spikeglx", "openephys"])
    def test_get_bad_channel_ids_assumptions(self, file_format, tmp_path):
        """
        Check that the assumptions the internal `_get_bad_channel_ids()`
        uses from the SI function are correct. Check both spikeglx
        and openephys because this is important to be correct.

        This ensures that 1) the order of labels output from `si.detect_bad_channels`
        matches `recording.get_channel_ids()` and that by default `detect_bad_channels`
        removes 'bad' channels as any of dead, noise and out.

        """
        detect_bad_channel_kwargs = self.get_bad_channel_kwargs()

        session = sw.Session(
            subject_path=sw.get_example_data_path(file_format) / "rawdata" / "sub-001",
            session_name="ses-001",
            file_format=file_format,
            run_names="all",
            output_path=tmp_path,
        )
        session.load_raw_data()

        recording = session._raw_runs[0]._raw["grouped"]
        channel_ids, labels = si.detect_bad_channels(
            recording, **detect_bad_channel_kwargs
        )

        bad_ids = self.ids_from_channel_label(
            "all", recording.get_channel_ids(), labels
        )

        assert (
            len(bad_ids) != 384
        ), "choose some defaults that dont remove all channels!"
        assert (
            len(bad_ids) != 0
        ), "choose some defaults that remove at least one channel!"

        assert bad_ids == list(channel_ids)

    def test_get_bad_channel_ids(self, session):
        """
        Test the spikewrap internal function `_get_bad_channel_ids()` that
        separates ids based on their label works as expected.
        """
        detect_bad_channel_kwargs = self.get_bad_channel_kwargs()

        recording = session._raw_runs[0]._raw["grouped"]

        channel_ids, labels = si.detect_bad_channels(
            recording, **detect_bad_channel_kwargs
        )
        assert (
            len(channel_ids) != 0
        ), "Somehow the test parameters are no longer triggering bad channel detection"

        # Loop instead of parameterise to avoid repeating above computation
        # Check the output from `_get_bad_channel_ids()` matches the output
        # as expected from the SI function.
        for label_to_test in ["out", "noise", "dead", ["out", "noise"]]:

            sw_bad_ids = _get_bad_channel_ids(
                recording, label_to_test, detect_bad_channel_kwargs
            )

            if not isinstance(label_to_test, list):
                label_to_test = [label_to_test]

            si_bad_ids = self.ids_from_channel_label(
                label_to_test, recording.get_channel_ids(), labels
            )

            assert (
                len(si_bad_ids) != 384
            ), "choose some defaults that dont remove all channels!"
            assert (
                len(si_bad_ids) != 0
            ), "choose some defaults that remove at least one channel!"

            assert sorted(sw_bad_ids) == sorted(si_bad_ids), f"failed {label_to_test}"
