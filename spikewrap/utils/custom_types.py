from typing import Literal, Tuple, Union

HandleExisting = Literal["overwrite", "skip_if_exists", "fail_if_exists"]
DeleteIntermediate = Tuple[
    Union[Literal["recording.dat"], Literal["temp_wh.dat"], Literal["waveforms"]], ...
]
