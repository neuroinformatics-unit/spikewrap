import os
import platform
from pathlib import Path
from typing import Literal

import spikeinterface.full as si
from spikeinterface.sorters.runsorter import SORTER_DOCKER_MAP

from spikewrap.utils import _checks


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


def _configure_run_sorter_method(
    sorter: str, run_sorter_method: str | Path, singularity_image_path: Path
) -> tuple[bool, Literal[False] | Path]:
    """ """
    kilosort_matlab_list = ["kilosort", "kilosort2", "kilosort2_5", "kilosort3"]
    matlab_list = kilosort_matlab_list + ["HDSort", "IronClust", "Waveclus"]

    run_singularity: Literal[False] | Path

    run_docker = run_singularity = False
    if run_sorter_method == "local":
        if sorter in matlab_list:
            raise ValueError("Some error")

    elif isinstance(run_sorter_method, str) or isinstance(run_sorter_method, Path):

        repo_path = Path(run_sorter_method)

        if not repo_path.is_dir():
            raise FileNotFoundError(f"No repository for {sorter} found at: {repo_path}")

        assert sorter in matlab_list, "MUST BE KILOSORT"

        if sorter in kilosort_matlab_list:
            pass
            # check mex files are found in kilosort and raise if not!
            # raise if not a real file.
            # if sorter == "":
            #    HDSortSorter.set_hdsort_path()

        assert Path(run_sorter_method)

        setter_functions = {
            "kilosort": si.KilosortSorter.set_kilosort_path,
            "kilosort2": si.Kilosort2Sorter.set_kilosort2_path,
            "kilosort2_5": si.Kilosort2_5Sorter.set_kilosort2_5_path,
            "kilosort3": si.Kilosort3Sorter.set_kilosort3_path,
            "HDSort": si.HDSortSorter.set_hdsort_path,
            "IronClust": si.IronClustSorter.set_ironclust_path,
            "Waveclus": si.WaveClusSorter.set_waveclus_path,
        }

        setter_functions[sorter](run_sorter_method)

    elif run_sorter_method == "docker":
        assert _checks._docker_desktop_is_running(), (
            f"The sorter {sorter} requires a virtual machine image to run, but "
            f"Docker is not running. Open Docker Desktop to start Docker."
        )
        run_docker = True

    elif run_sorter_method == "singularity":
        if not _checks._system_call_success("singularity version"):
            raise RuntimeError(
                "`singularity` is not installed, cannot run the sorter with singularity."
            )

        run_singularity = singularity_image_path

    return run_docker, run_singularity
