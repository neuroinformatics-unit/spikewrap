import os

import pytest
import spikeinterface

from spikewrap.utils.managing_images import download_all_sorters


class TestManagingImages:
    @pytest.mark.parametrize("to_hpc_path", [True, False])
    def test_download_all_sorters(self, tmp_path, monkeypatch, to_hpc_path):
        """
        Test that `download_all_sorters` downloads the correct sorters.
        This function will either download to the hpc path set in
        configs.backend.hpc.hpc_sorter_images_path or to the
        current working folder.

        If `to_hpc_path` is `True`, the function `hpc_sorter_images_path()`
        is called to get the path, so we need to monkeypatch it with
        a pytest temporary test path.

        Otherwise, we can just change the cwd to the `temp_path`.

        Then, simply check that the expected paths are created and
        expected image files exist.
        """
        if to_hpc_path:

            def hpc_sorter_images_path2():
                return str(tmp_path)

            monkeypatch.setattr(
                "spikewrap.utils.managing_images.hpc_sorter_images_path",
                hpc_sorter_images_path2,
            )
        else:
            os.chdir(tmp_path)

        download_all_sorters(save_to_config_location=to_hpc_path)

        assert (out_path := tmp_path / spikeinterface.__version__).is_dir()

        downloaded_images = [path_.stem for path_ in out_path.glob("*.sif")]

        assert "kilosort2-compiled-base" in downloaded_images
        assert "kilosort2_5-compiled-base" in downloaded_images
        assert "kilosort3-compiled-base" in downloaded_images
