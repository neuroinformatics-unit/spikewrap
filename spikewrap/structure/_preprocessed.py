import spikeinterface.full as si
from spikewrap.process._preprocessing import fill_with_preprocessed_recordings
from spikewrap.utils import _utils
from spikewrap.configs._backend import canon


class Preprocessed:
    """
    This class is immutable.

    responsibilities :
      - hold list of preprocessed recordings
      - write these to disk

    TODO:
    - decide on dtype for all computation.
    """

    def __init__(self, recording, pp_steps, output_path, name):

        self._pp_steps = pp_steps
        self._output_path = output_path
        self._name = name

        self._data = {"0-raw": recording}

        if name == canon.grouped_shankname():
            self._preprocessed_path = output_path / canon.preprocessed_folder()
        else:
            self._preprocessed_path = output_path / canon.preprocessed_folder() / name

        fill_with_preprocessed_recordings(
            self._data,
            self._pp_steps
        )

    @property
    def data(self):
        """
        """
        return self._data

    def save_binary(
        self, chunk_size # : Optional[int]
    ) -> None:
        """
        Save the fully preprocessed data (i.e. last step in the
        preprocessing chain) to binary file. This is required for sorting.
        """
        recording, __ = _utils.get_dict_value_from_step_num(
            self._data, "last"
        )

        if chunk_size is None:
            chunk_size = _utils.get_default_chunk_size(recording)

        recording.save(
            folder=self._preprocessed_path / canon.preprocessed_bin_folder(),
            chunk_size=chunk_size,
        )
