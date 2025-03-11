from __future__ import annotations

import pytest

from spikewrap.process._loading import get_raw_run_paths


class TestSpikeGLXRunLoading:

    def make_spikeglx_files(self, run_path):
        for filename in [
            "file_g0_g0_t0.imec0.ap.bin",
            "file_g0_g0_t0.imec0.ap.meta",
        ]:
            with open(run_path / filename, "w") as file:
                file.write("\n")

    @pytest.mark.parametrize("is_multi_layer", [True, False])
    def test_spikeglx_named_run_folder(self, tmp_path, is_multi_layer):
        """
        Check that runs are detected both if they are a run
        containing spikeglx output folders, or directly containing
        spikeglx output files.
        """
        ses_path = tmp_path / "project" / "rawdata" / "sub-001" / "ses-001"
        run_path = ses_path / "ephys" / "run_001"

        if is_multi_layer:
            run_path = run_path / "run_g0_t0_imec0"

        run_path.mkdir(parents=True)
        self.make_spikeglx_files(run_path)

        check_run_path = get_raw_run_paths("spikeglx", ses_path, "all")

        assert len(check_run_path) == 1

        if is_multi_layer:  # TODO: this is not nice, probably should be two tests.
            assert check_run_path[0] == run_path.parent
        else:
            assert check_run_path[0] == run_path
