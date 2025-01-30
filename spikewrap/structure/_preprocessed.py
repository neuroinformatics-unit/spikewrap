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
    This class represents a single recording and its full preprocessing chain.
    This is a class used internally by spikewrap.

    This class should be treated as immutable after initialisation.

    Preprocessed recordings are held in self._data, a dict with
    keys as a str representing the current step in the preprocessing chain,
    e.g. "0-raw", "0-raw_1-phase_shift_2-bandpass_filter"
    and value the corresponding preprocessed recording.

    Parameters
    ----------
        recording :
            The raw SpikeInterface recording (prior to preprocessing).
        pp_steps :
            Preprocessing configuration dictionary (see configs documentation).
        output_path :
            Path to output the saved fully preprocessed (i.e. last step in the chain)
            recording to, with `save_binary()`.
    """

    def __init__(
        self, recording: BaseRecording, pp_steps: dict, output_path: Path, name: str
    ):
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
        Save the fully preprocessed data (i.e. last step in the
        preprocessing chain) to binary file.

        Parameters
        ----------
        chunk_duration_s :
            Writing chunk size in seconds.
        """
        recording, __ = _utils._get_dict_value_from_step_num(self._data, "last")

        recording.save(
            folder=self._preprocessed_path / canon.preprocessed_bin_folder(),
            chunk_duration=chunk_duration_s,
        )
