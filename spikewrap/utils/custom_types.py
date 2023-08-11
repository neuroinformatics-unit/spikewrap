from typing import Literal, Tuple

HandleExisting = Literal["overwrite", "load_if_exists", "fail_if_exists"]
DeleteIntermediate = Tuple[
    Literal["recording.dat"], Literal["temp_wh.dat"], Literal["waveforms"]  # see #82
]
