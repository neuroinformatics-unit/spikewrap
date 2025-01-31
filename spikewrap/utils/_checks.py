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
