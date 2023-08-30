import platform
import re
import subprocess
import sys
from pathlib import Path

import toml

from spikewrap.utils import utils


def check_environment() -> None:
    """
    Check that a virtual machine manager is installed (Singularity for Linux,
    Docker for macOS or Windows). Perform a minimal check that cuda drivers
    are installed. Finally, check all dependencies listed in pyproject.toml
    are installed in the environment.
    """
    check_virtual_machine()
    check_cuda()
    _check_pip_dependencies()


def check_virtual_machine() -> bool:
    """
    Check that a virtual machine manager is installed on the
    system (singularity for Linux, Docker otherwise). Note that
    sorters that can run natively in python
    do not require virtual machines, only Kilosort < 4 at present.

    If the virtual machine manager is not found on the system, print
    a link to installation instructions.
    """
    if platform.system() == "Linux":
        has_vm = _system_call_success("singularity version")
        name = "Singularity"
        link = (
            "https://docs.sylabs.io/guides/main/user-guide/quick_start.html#quick"
            "-installation-steps"
        )
    else:
        has_vm = _system_call_success("docker -v")
        name = "Docker"
        if platform.system() == "Windows":
            link = "https://docs.docker.com/desktop/install/windows-install/"
        else:
            link = "https://docs.docker.com/desktop/install/mac-install/"

    if has_vm:
        utils.message_user(
            f"{name} is installed. Sorters such as Kilosort that\n"
            f"cannot be run in native Python will run in a virtual machine."
        )
        return True

    utils.message_user(
        f"{name} is not installed. Sorters such as Kilosort that\n"
        f"cannot be run in native Python are not available. To install\n"
        f"{name}, see: {link}"
    )
    return False


def docker_desktop_is_running():
    """
    Note "docker -v" shows if docker is installed but not necessarily
    running. "docker ps" requires docker to be running, which can
    be achieved by opening Docker Desktop.
    """
    return _system_call_success("docker ps")


def check_cuda() -> bool:
    """
    Perform a very basic check that NVIDIA drivers are installed. This
    however does not ensure GPU processing will work without error.
    """
    if _system_call_success("nvidia-smi"):
        utils.message_user("NVIDIA GPU drivers detected on the system.")
        return True
    else:
        utils.message_user(
            "NVIDIA GPU drivers not detected. Sorters that require\n"
            "NVIDIA GPU such as Kilosort will not be able to run."
        )
        return False


def _check_pip_dependencies() -> None:
    """
    Perform a confidence check that all dependencies listed
    in the pyproject.toml are installed in the current environment.
    """
    utils.message_user("Checking Python dependencies...")
    pyproject_path = (
        Path(sys.modules["spikewrap"].__path__[0]).parent / "pyproject.toml"
    )
    pyproject_toml = toml.load(pyproject_path.as_posix())

    pip_list = subprocess.run(
        "pip list",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    ).stdout.decode()

    all_deps_installed = True
    for dep in pyproject_toml["project"]["dependencies"]:
        dep_name = re.split("<|>|=", dep)[0]

        if dep_name not in pip_list:
            all_deps_installed = False
            utils.message_user(
                f"The dependency {dep_name} was not found in the current environment using pip.\n"
                f"Ensure all dependencies are installed by reinstalling SpikeWrap."
            )
    if all_deps_installed:
        utils.message_user("All python dependencies are installed.")


def _system_call_success(command: str) -> bool:
    return (
        subprocess.run(
            command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )
