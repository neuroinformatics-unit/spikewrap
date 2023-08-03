import platform
import re
import subprocess
from pathlib import Path
import toml
from swc_ephys.utils import utils


def check_environment() -> None:
    """ """
    _check_virtual_machine()
    _check_cuda()
    _check_pip_dependencies()


def _check_virtual_machine() -> bool:
    """"""
    if platform.system() == "Linux":
        has_vm = _system_call_sucess("singularity")
        name = "Singularity"
        link = (
            "https://docs.sylabs.io/guides/main/user-guide/quick_start.html#quick"
            "-installation-steps"
        )
    else:
        has_vm = _system_call_sucess("docker -v")
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
    return _system_call_sucess("docker ps")


def _check_cuda() -> None:
    """"""
    if _system_call_sucess("nvidia-smi"):
        utils.message_user("NVIDIA GPU drivers detected on the system.")
    else:
        utils.message_user(
            "NVIDIA GPU drivers not detected. Sorters that require\n"
            "GPU such as Kilosort will not be able to run."
        )


def _check_pip_dependencies() -> None:
    """"""
    utils.message_user("Checking Python dependencies...")

    pyproject_path = Path(__file__).parents[-4] / "pyproject.toml"
    pyproject_toml = toml.load(pyproject_path.as_posix())

    pip_list = subprocess.run(
        "pip list",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=None,
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


def _system_call_sucess(command: str) -> bool:
    return (
        subprocess.run(
            command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )
