from __future__ import annotations

import probeinterface as pi
import pytest
from base import BaseTest

import spikewrap as sw
from spikewrap.utils import _utils
import matplotlib
import copy

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

    @pytest.mark.parametrize("save_preprocessed", [True, False])
    def test_plot_probe_saves_image(self, tmp_path, save_preprocessed):
        """
        Test that `plot_probe()` generates and saves the probe plot image.
        It can be saved either automatically, when preprocessing is performed,
        or explicitly with the plot_probe method.
        """
        session = sw.Session(
            sw.get_example_data_path() / "rawdata" / "sub-001",
            "ses-001",
            "spikeglx",
            run_names="all",
            output_path=tmp_path
        )

        if save_preprocessed:
            session.preprocess(self.get_pp_steps(), per_shank=False)
            session.save_preprocessed(overwrite=True)
        else:
            fig = session.plot_probe(save=True)
            # just do this check for good measure here
            assert isinstance(fig, matplotlib.figure.Figure)

        saved_plot_path = session._output_path / "probe_plot.png"

        assert saved_plot_path.exists()

    def test_plot_probe_raises_on_probe_mismatch(self):
        """
        Simulate mismatched probes across runs to check error is raised.
        """
        session = sw.Session(
            sw.get_example_data_path() / "rawdata" / "sub-001",
            "ses-001",
            "spikeglx",
            run_names="all",
        )
        session.load_raw_data()

        probe = self.get_mock_probe()
        different_probe = copy.deepcopy(probe)
        different_probe._contact_positions += 1

        session._raw_runs[0].get_probe = lambda: probe
        session._raw_runs[1].get_probe = lambda: different_probe

        with pytest.raises(
            ValueError,
            match="The probe for run: run-001_g0_imec0 is different than for run: run-002_g0_imec0"
        ):
            session.get_probe()