from __future__ import annotations

import os
import platform
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Tuple, Union

import spikeinterface
from spikeinterface.sorters.runsorter import SORTER_DOCKER_MAP

from spikewrap.utils import checks, utils

if TYPE_CHECKING:
    from spikewrap.data_classes.sorting import SortingData


def move_singularity_image_if_required(
    sorting_data: SortingData,
    singularity_image: Optional[Union[Literal[True], str]],
    sorter: str,
) -> None:
    """
    On Linux, images are cased to the sorting_data base folder
    by default by SpikeInterface. To avoid re-downloading
    images, these are moved to home directory. This is only required
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

        path_to_image = sorting_data.base_path / get_sorter_image_name(sorter)

        destination = get_local_sorter_path(sorter).parent
        destination.mkdir(exist_ok=True, parents=True)

        shutil.move(path_to_image, destination)


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

    if get_local_sorter_path(sorter).is_file():
        singularity_image = str(get_local_sorter_path(sorter))
    else:
        singularity_image = True

    return singularity_image


def get_local_sorter_path(
    sorter: str, spikeinterface_version: Optional[str] = None
) -> Path:
    """
    Return the path to a sorter singularity image. The sorters are
    stored by spikewrap in the home folder.

    Parameters
    ----------
    sorter : str
        The name of the sorter to get the path to (e.g. kilosort2_5).

    spikeinterface_version : Optional[str]
        The spikeinterface version from which the sorter was stored.
        Otherwise, use the currently installed version.

    Returns
    ---------
    local_path : Path
        The path to the sorter image on the local machine.
    """
    if spikeinterface_version is None:
        spikeinterface_version = spikeinterface.__version__

    local_path = (
        Path.home()
        / ".spikewrap"
        / "sorter_images"
        / sorter
        / spikeinterface_version
        / get_sorter_image_name(sorter)
    )

    return local_path


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


def download_all_sorters() -> None:
    """
    Convenience function to download all sorters in the
    default homee directory.

    The SI images are stored at:
        https://github.com/SpikeInterface/spikeinterface-dockerfiles
    """

    assert platform.system() == "Linux", (
        "Downloading all sorters is only necessary for `singularity`. "
        "Must be on Linux machine."
    )
    from spython.main import Client

    supported_sorters = utils.canonical_settings("supported_sorters")
    can_run_locally = utils.canonical_settings("sorter_can_run_locally")

    for sorter in supported_sorters:
        if sorter not in can_run_locally:
            save_to_path = get_local_sorter_path(sorter)
            save_to_path_parent = save_to_path.parent

            if save_to_path.is_file():
                raise FileExistsError(f"Image folder already exists at {save_to_path}")

            save_to_path_parent.mkdir(exist_ok=True, parents=True)
            os.chdir(save_to_path_parent)

            container_image = SORTER_DOCKER_MAP[sorter]
            Client.pull(f"docker://{container_image}")
