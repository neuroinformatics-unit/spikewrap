from __future__ import annotations

from pathlib import Path
from typing import Literal


def get_example_data_path(
    file_format: Literal["spikeglx", "openephys"] = "spikeglx"
) -> Path:
    """
    Get the path to the example data directory. This contains a
    very small example spikeglx dataset in NeuroBlueprint format.

    Returns
    -------
    Path
        Path to the root folder of the example dataset.
    """
    if file_format not in ["spikeglx", "openephys"]:
        raise ValueError("`file_format` not recognised.")

    return Path(__file__).parents[1] / "examples" / "example_tiny_data" / file_format
