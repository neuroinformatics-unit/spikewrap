import platform

import pytest
import spikeinterface

from spikewrap.utils import checks

HAS_VM_ON_LINUX = platform.system() == "Linux" and checks.check_virtual_machine()

from spikewrap.utils.managing_images import (
    download_all_sorters,
    get_sorter_image_name,
)


@pytest.mark.skipif(
    "HAS_VM_ON_LINUX is False", reason="Test requires singularity on Linux."
)
class TestManagingImages:
    def test_download_all_sorters(self, tmp_path, monkeypatch):
        """
        Test that `download_all_sorters` downloads the correct sorters.
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
