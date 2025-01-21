import platform
import re
import subprocess
import sys
from pathlib import Path

import toml

from spikewrap.utils import _utils


def system_call_success(command: str) -> bool:
    return (
        subprocess.run(
            command, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ).returncode
        == 0
    )