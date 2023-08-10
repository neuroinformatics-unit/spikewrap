from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Tuple, Union

from . import checks

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
) -> Tuple[
    Optional[Union[Literal[True], str]], Optional[bool]
]:  # cannot set this to Literal[True], for unknown reason.
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
    can_run_locally = ["spykingcircus", "mountainsort5", "tridesclous"]

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
        assert checks._check_virtual_machine()

        if platform.system != "Linux":
            assert (
                checks.docker_desktop_is_running()
            ), "Docker is not running. Open Docker Desktop to start Docker."

    return singularity_image, docker_image


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
    base_path = Path("/ceph/neuroinformatics/neuroinformatics/scratch/sorter_images")
    sorter_path = base_path / sorter / get_sorter_image_name(sorter)
    return sorter_path


def get_sorter_image_name(sorter: str) -> str:
    """
    Get the sorter image name, as defined by how
    SpikeInterface names the docker images it provides.

    Parameters
    ----------
    sorter : str
        The name of the sorter to get the path to (e.g. kilosort2_5).

    Returns
    -------
    sorter_name : str
        The SpikeInterface filename of the docker image for that sorter.
    """
    if "kilosort" in sorter:
        sorter_name = f"{sorter}-compiled-base.sif"
    else:
        if sorter == "spykingcircus":
            sorter = "spyking-circus"
        sorter_name = f"{sorter}-base.sif"
    return sorter_name
