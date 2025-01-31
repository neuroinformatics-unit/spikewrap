from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from spikeinterface.core import BaseRecording

from spikewrap.configs._backend import canon
from spikewrap.process._preprocessing import _fill_with_preprocessed_recordings
from spikewrap.utils import _utils


class Preprocessed:
    """
    Class for holding and managing the preprocessing
    of a SpikeInterface recording.

    Parameters
    ----------
    recording
        SpikeInterface raw recording object to be preprocessed.
    pp_steps
        Dictionary specifying preprocessing steps, see ``configs`` documentation.
    output_path
        Path where preprocessed recording is to be saved (i.e. run folder).
    """

    def __init__(
        self, recording: BaseRecording, pp_steps: dict, output_path: Path, name: str
    ):
        # These parameters should be treated as constant and never changed
        # during the lifetime of the class. Use the properties (which do not
        # expose a setter) for both internal and external calls.
        if name == canon.grouped_shankname():
            self._preprocessed_path = output_path / canon.preprocessed_folder()
        else:
            self._preprocessed_path = output_path / canon.preprocessed_folder() / name

        self._data = {"0-raw": recording}

        _fill_with_preprocessed_recordings(self._data, pp_steps)

    # -----------------------------------------------------------------------
    # Public Functions
    # -----------------------------------------------------------------------

    def save_binary(self, chunk_duration_s: float = 2.0) -> None:
        """
        Save the fully preprocessed data (i.e. last step in
        the preprocessing chain) to binary file.

        Parameters
        ----------
        chunk_duration_s
            Writing chunk size in seconds.
        """
        recording, __ = _utils._get_dict_value_from_step_num(self._data, "last")

        recording.save(
            folder=self._preprocessed_path / canon.preprocessed_bin_folder(),
            chunk_duration=f"{chunk_duration_s}s",
        )
