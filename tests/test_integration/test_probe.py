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

    def test_plot_probe_saves_image(self, tmp_path):
        """
        Test that `plot_probe()` generates and saves the probe plot image.
        """
        session = sw.Session(
            sw.get_example_data_path() / "rawdata" / "sub-001",
            "ses-001",
            "spikeglx",
            run_names="all",
        )

        session.preprocess(self.get_pp_steps(), per_shank=False)
        session.save_preprocessed(overwrite=True)

        fig = session.plot_probe(output_folder=tmp_path, show=False)
        assert fig is not None

        # Check that probe plot was saved
        saved_plot = tmp_path / "probe_plots" / "probe_plot.png"
        assert saved_plot.exists()

    def test_plot_probe_raises_on_empty_session(self):
        """
        Test that calling `plot_probe()` with no preprocessed runs raises an error.
        """
        session = sw.Session(
            sw.get_example_data_path() / "rawdata" / "sub-001",
            "ses-001",
            "spikeglx",
            run_names="all",
        )

        with pytest.raises(RuntimeError, match="No runs available in this session."):
            session.plot_probe()

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
        session.preprocess(self.get_pp_steps(), per_shank=False)

        # Monkey-patch mismatched probe structure
        session._pp_runs[1].get_probe = lambda: {"shank_0": self.get_mock_probe()}
        session._pp_runs[0].get_probe = lambda: {"shank_1": self.get_mock_probe()}

        with pytest.raises(
            ValueError, match="Mismatch in shank structure across runs."
        ):
            session.plot_probe()

    def test_get_probe_dict_structure(self):
        """
        Verify get_probe() returns a dict with correct keys and Probe objects.
        """
        session = sw.Session(
            sw.get_example_data_path() / "rawdata" / "sub-001",
            "ses-001",
            "spikeglx",
            run_names="all",
        )
        session.preprocess(self.get_pp_steps(), per_shank=True)
        run = session._pp_runs[0]

        probe_dict = run.get_probe()
        assert isinstance(probe_dict, dict)
        assert all(isinstance(k, str) for k in probe_dict)
        assert all(isinstance(v, pi.Probe) for v in probe_dict.values())

    def test_get_probe_raises_when_data_missing(self):
        """
        Ensure get_probe raises a RuntimeError if no preprocessed data is available.
        """
        from pathlib import Path

        from spikewrap.structure._preprocess_run import PreprocessedRun

        dummy_run = PreprocessedRun(
            raw_data_path=Path("/tmp"),
            ses_name="ses-001",
            run_name="run-001",
            file_format="spikeglx",
            session_output_path=Path("/tmp/out"),
            preprocessed_data={},  # Empty dict simulates missing data
            pp_steps={},
        )

        with pytest.raises(RuntimeError, match="No preprocessed data found for run"):
            dummy_run.get_probe()

    def test_plot_probe_with_custom_output_folder(self, tmp_path):
        """
        Ensure the plot is saved in the specified output folder.
        """
        session = sw.Session(
            sw.get_example_data_path() / "rawdata" / "sub-001",
            "ses-001",
            "spikeglx",
            run_names="all",
        )

        session.preprocess(self.get_pp_steps(), per_shank=False)
        session.save_preprocessed(overwrite=True)

        custom_output = tmp_path / "custom_out"
        fig = session.plot_probe(output_folder=custom_output, show=False)

        expected_path = custom_output / "probe_plots" / "probe_plot.png"
        assert expected_path.exists()
        assert fig is not None
