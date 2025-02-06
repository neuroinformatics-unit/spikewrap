from pathlib import Path

import numpy as np
import probeinterface as pi
import pytest

import spikewrap as sw

# TODO: FIX ORDER IN DOCS!


class TestSetProbe:

    @pytest.mark.parametrize("per_shank", [True, False])
    @pytest.mark.parametrize("concat_runs", [True, False])
    def test_set_probe(self, per_shank, concat_runs):
        """
        Check that setting a passed probe on the recording allows it to be
        run. Note this is a mock probe, not the real probe used for the
        recorded data.
        """
        mock_probe = self.get_mock_probe()

        session = sw.Session(
            self.get_no_probe_sub_path(),
            "ses-001",
            "openephys",
            "all",
            probe=mock_probe,
        )

        session.preprocess("neuropixels+kilosort2_5", per_shank, concat_runs)

        all_run_data = []
        for run in session._runs:
            for rec in run._raw.values():
                all_run_data.append(rec)

        assert all([isinstance(rec.get_probe(), pi.Probe) for rec in all_run_data])

    def test_no_probe_error(self):
        """
        Check an error is thrown when no probe is set.
        """
        session = sw.Session(
            self.get_no_probe_sub_path(), "ses-001", "openephys", "all", probe=None
        )

        with pytest.raises(RuntimeError) as e:
            session.preprocess(
                "neuropixels+kilosort2_5", per_shank=False, concat_runs=False
            )

        assert "No probe is attached to this recording." in str(e.value)

    def test_probe_already_set_error(self):
        """
        Check that an error is thrown if the probe is auto-detected
        but a user tries to manually set the probe.
        """
        mock_probe = self.get_mock_probe()

        session = sw.Session(
            sw.get_example_data_path() / "rawdata" / "sub-001",
            "ses-001",
            "spikeglx",
            "all",
            probe=mock_probe,
        )

        with pytest.raises(RuntimeError) as e:
            session.preprocess(
                "neuropixels+kilosort2_5", per_shank=False, concat_runs=False
            )

        assert "A probe was already auto-detected." in str(e.value)

    # Getters
    # ----------------------------------------------------------------------------------

    def get_no_probe_sub_path(self):
        return (
            Path(__file__).parent.parent
            / "test_data"
            / "no_probe"
            / "rawdata"
            / "sub-001"
        )

    def get_mock_probe(self):
        mock_probe = pi.get_probe("neuropixels", "NP2014")
        mock_probe = mock_probe.get_slice(np.arange(16))
        return mock_probe
