import os
import platform
from pathlib import Path

from spikeinterface.sorters.runsorter import SORTER_DOCKER_MAP


def _download_sorter(sorter: str, sorter_path: Path) -> None:
    """
    The SI images are stored at:
        https://github.com/SpikeInterface/spikeinterface-dockerfiles

    TODO: test and ask carefully how the installation works on
    already downloaded docker images. multiprocessing, shared between
    multiple nodes...
    """
    assert platform.system() == "Linux", (
        "Downloading all sorters is only necessary for `singularity`. "
        "Must be on Linux machine."
    )
    from spython.main import Client

    sorter_path_parent = sorter_path.parent

    if sorter_path.is_file():
        raise FileExistsError(f"Image folder already exists at {sorter_path}")

    sorter_path_parent.mkdir(exist_ok=True, parents=True)
    os.chdir(sorter_path_parent)

    container_image = SORTER_DOCKER_MAP[sorter]
    Client.pull(f"docker://{container_image}")
