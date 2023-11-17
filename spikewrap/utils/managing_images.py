from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Tuple, Union

import spikeinterface
from spikeinterface.sorters.runsorter import SORTER_DOCKER_MAP

from ..configs.backend.hpc import hpc_sorter_images_path
from . import checks, utils

if TYPE_CHECKING:
    from ..data_classes.sorting import SortingData


def move_singularity_image_if_required(
    sorting_data: SortingData,
    singularity_image: Optional[Union[Literal[True], str]],
    sorter: str,
) -> None:
    """
    On Linux, images are cased to the sorting_data base folder
    by default by SpikeInterface. To avoid re-downloading
    images, these are moved to a pre-determined folder (home
    for local, pre-set on an HPC). This is only required
    for singularity, as docker-desktop handles all image
    storage.

    Parameters
    ----------

    sorting_data: SortingData
        Spikewrap SortingData object.

    singularity_image: Optional[Union[Literal[True], Path]]
        Holds either a path to an existing (stored) sorter, or
        `True`. If `True`, no stored sorter image exists and so
        we move it. The next time sorting is performed, it will use
        this stored image.

    sorter : str
        Name of the sorter.
    """
    if singularity_image is True:
        assert (
            platform.system() == "Linux"
        ), "Docker Desktop should be used on Windows or macOS."
        store_singularity_image(sorting_data.base_path, sorter)


def get_image_run_settings(
    sorter: str,
) -> Tuple[Optional[Union[Literal[True], str]], Optional[Literal[True]]]:
    """
    Determine how to run the sorting, either locally or in a container
    if required (e.g. kilosort2_5). On windows, Docker is used,
    otherwise singularity. Docker images are handled by Docker-desktop,
    but singularity image storage is handled internally, see
    `move_singularity_image_if_required()`.

    Parameters
    ----------

    sorter : str
        Sorter name.
    """
    can_run_locally = utils.canonical_settings("sorter_can_run_locally")

    if sorter in can_run_locally:
        singularity_image = docker_image = None
    else:
        if platform.system() == "Windows":
            singularity_image = None
            docker_image = True
        else:
            singularity_image = get_singularity_image(sorter)
            docker_image = None

    if singularity_image or docker_image:
        assert checks.check_virtual_machine()

        if platform.system() != "Linux":
            assert checks.docker_desktop_is_running(), (
                f"The sorter {sorter} requires a virtual machine image to run, but "
                f"Docker is not running. Open Docker Desktop to start Docker."
            )

    return singularity_image, docker_image  # type: ignore


def store_singularity_image(base_path: Path, sorter: str) -> None:
    """
    When running locally, SpikeInterface will pull the docker image
    to the current working directly. Move this to home/.spikewrap
    so they can be used again in future and are centralised.

    Parameters
    ----------
    base_path : Path
        Base-path on the SortingData object, the path that holds
        `rawdata` and `derivatives` folders.

    sorter : str
        Name of the sorter for which to store the image.
    """
    path_to_image = base_path / get_sorter_image_name(sorter)
    shutil.move(path_to_image, get_local_sorter_path(sorter).parent)


def get_singularity_image(sorter: str) -> Union[Literal[True], str]:
    """
    Get the path to a pre-installed system singularity image. If none
    can be found, set to True. In this case SpikeInterface will
    pull the image to the current working directory, and
    this will be moved after sorting
    (see store_singularity_image).

    Parameters
    ----------
    sorter : str
        Name of the sorter to get the image for.

    Returns
    -------
    singularity_image [ Union[Literal[True], str]
        If `str`, the path to the singularity image. Otherwise if `True`,
        this tells SpikeInterface to pull the image.
    """
    singularity_image: Union[Literal[True], str]

    if get_hpc_sorter_path(sorter).is_file():
        singularity_image = str(get_hpc_sorter_path(sorter))

    elif get_local_sorter_path(sorter).is_file():
        singularity_image = str(get_local_sorter_path(sorter))
    else:
        singularity_image = True

    return singularity_image


def get_local_sorter_path(sorter: str) -> Path:
    """
    Return the path to a sorter singularity image. The sorters are
    stored by spikewrap in the home folder.

    Parameters
    ----------
    sorter : str
        The name of the sorter to get the path to (e.g. kilosort2_5).

    Returns
    ---------
    local_path : Path
        The path to the sorter image on the local machine.
    """
    local_path = (
        Path.home() / ".spikewrap" / "sorter_images" / get_sorter_image_name(sorter)
    )
    local_path.parent.mkdir(exist_ok=True, parents=True)
    return local_path


def get_hpc_sorter_path(sorter: str) -> Path:
    """
    Return the path to the sorter image on the SWC HCP (ceph).

    Parameters
    ----------
    sorter : str
        The name of the sorter to get the path to (e.g. kilosort2_5).

    Returns
    -------
    sorter_path : Path
        The base to the sorter image on SWC HCP (ceph).
    """
    base_path = Path(hpc_sorter_images_path())
    sorter_path = (
        base_path / sorter / spikeinterface.__version__ / get_sorter_image_name(sorter)
    )
    return sorter_path


def get_sorter_image_name(sorter: str) -> str:
    """
    Get the sorter image name, as defined by how
    SpikeInterface names the images it provides.

    Parameters
    ----------
    sorter : str
        The name of the sorter to get the path to (e.g. kilosort2_5).

    Returns
    -------
    sorter_name : str
        The SpikeInterface filename of the docker image for that sorter.
    """
    # use spikeinterface sorter SORTER_DOCKER_MAP

    if "kilosort" in sorter:
        sorter_name = f"{sorter}-compiled-base.sif"
    else:
        if sorter == "spykingcircus":
            sorter = "spyking-circus"
        sorter_name = f"{sorter}-base.sif"
    return sorter_name


def download_all_sorters(save_to_config_location: bool = True) -> None:
    """
    Convenience function to download all sorters and move them to
    the HPC path (set in configs/backend/hpc.py). This should be run
    when upgrading to a new version of spikeinterface, to ensure
    the latest image versions are used.

    The SI images are stored at:
        https://github.com/SpikeInterface/spikeinterface-dockerfiles

    Parameters
    ----------

    save_to_config_location : bool
        If `True`, the sorters are saved in the default hpc
        sorter images path specified in configs/backend/hpc.py
        If `False`, the sorters are downloaded to the current
        working direction.
    """

    assert platform.system() == "Linux", (
        "Downloading all sorters is only necessary for `singularity`. "
        "Must be on Linux machine."
    )
    from spython.main import Client

    spikeinterface_version = spikeinterface.__version__

    if save_to_config_location:
        save_to_path = Path(hpc_sorter_images_path()) / spikeinterface_version
    else:
        save_to_path = Path(os.getcwd()) / spikeinterface_version

    if save_to_path.is_dir():
        raise FileExistsError(f"Image folder already exists at {save_to_path}")

    save_to_path.mkdir()
    os.chdir(save_to_path)

    supported_sorters = utils.canonical_settings("supported_sorters")
    can_run_locally = utils.canonical_settings("sorter_can_run_locally")

    for sorter in supported_sorters:
        if sorter not in can_run_locally:
            container_image = SORTER_DOCKER_MAP[sorter]
            Client.pull(f"docker://{container_image}")
