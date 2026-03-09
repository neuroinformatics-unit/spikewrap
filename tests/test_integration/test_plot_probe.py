from __future__ import annotations

import copy

import probeinterface as pi
import pytest
from base import BaseTest

import spikewrap as sw
from spikewrap.utils import _utils
import matplotlib

class TestPlotProbe(BaseTest):

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

