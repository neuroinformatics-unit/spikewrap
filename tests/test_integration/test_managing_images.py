import spikeinterface

from spikewrap.utils.managing_images import (
    download_all_sorters,
    get_sorter_image_name,
)


class TestManagingImages:
    def test_download_all_sorters(self, tmp_path, monkeypatch):
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

        def new_base_path():
            return tmp_path

        monkeypatch.setattr(
            "spikewrap.utils.managing_images.Path.home",
            new_base_path,
        )

        download_all_sorters()

        for sorter in ["kilosort2", "kilosort2_5", "kilosort3"]:
            assert (
                out_path := tmp_path
                / ".spikewrap"
                / "sorter_images"
                / sorter
                / spikeinterface.__version__
            ).is_dir()

            assert (
                out_path / get_sorter_image_name(sorter)
            ).is_file(), f".sif file was not found for {sorter}"
