import subprocess


def _system_call_success(command: str) -> bool:
    """
    Execute a system call and return its return code.

    Parameters
    ----------
    command
        The system command to execute.

    Returns
    -------
    bool
        True if the command executes successfully (return code is 0), False otherwise.
    """
    return (
        subprocess.run(
            command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )


def _docker_desktop_is_running():
    """
    Note "docker -v" shows if docker is installed but not necessarily
    running. "docker ps" requires docker to be running, which can
    be achieved by opening Docker Desktop.
    """
    return _system_call_success("docker ps")
