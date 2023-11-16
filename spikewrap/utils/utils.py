from __future__ import annotations

import copy
import os
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable, Dict, List, Literal, Tuple, Union

import numpy as np
import yaml


def update(dict_, ses_name, run_name, value):
    try:
        dict_[ses_name][run_name] = value
    except KeyError:
        dict_[ses_name] = {run_name: value}

def message_user(message: str) -> None:
    """
    Method to interact with user.

    Parameters
    ----------
    message : str
        Message to print.
    """
    print(f"\n{message}")
