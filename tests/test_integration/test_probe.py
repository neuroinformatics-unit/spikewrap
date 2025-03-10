from __future__ import annotations

import probeinterface as pi
import pytest
from base import BaseTest

import spikewrap as sw
from spikewrap.utils import _utils


class TestSetProbe(BaseTest):

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

        session.preprocess(self.get_pp_steps(), per_shank, concat_runs)

        all_run_data = []
        for run in session._pp_runs:
            for prepro_dict in run._preprocessed.values():
                rec, _ = _utils._get_dict_value_from_step_num(prepro_dict, "last")
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
            session.preprocess(self.get_pp_steps(), per_shank=False, concat_runs=False)

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
            session.preprocess(self.get_pp_steps(), per_shank=False, concat_runs=False)

        assert "A probe was already auto-detected." in str(e.value)
