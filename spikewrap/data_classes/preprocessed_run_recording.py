from pathlib import Path
from typing import Dict, List, Literal, Optional, Tuple, Union

import spikeinterface as si


class PreprocessedRunRecording:
    """ """

    def __init__(
        self, file_path: Optional[Union[str, Path]] = None, data: Optional[Dict] = None
    ):
        self.data = {}

        if file_path is not None:
            file_path = Path(file_path)
            self.validate_file_path(file_path)
            self.load_binary_data(file_path)
        else:
            assert isinstance(data, Dict), "TODO"
            self.data = data

    def validate_file_path(self, file_path: Path) -> None:
        """
        does make some assumptiosn this is an spikewrap folder.
        """
        if not file_path.is_dir():
            raise FileNotFounderror(
                f"The preprocessing folder expected at {file_path} does not exist."
            )

        if file_path.stem != "si_recording":
            raise ValueError(
                f"The folder path passed to PreprocessRunRecording must "
                f"be called 'si_recording' as it must be a valid output"
                f"from spikewrap preprocessing. The passed path was"
                f"{file_path}"
            )

        if file_path.parent.stem != "preprocessing":
            raise ValueError(
                "The folder that `si_recording` is in does not"
                "seem to be a spikewrap preprocessing folder."
                "Please check the preprocessing step."
            )

    def load_binary_data(self, file_path: Path) -> None:
        folder_contents, shank_type = self.get_folder_contents_and_shank_type(file_path)

        if shank_type == "single":
            self.data["0"] = si.load_extractor(file_path)
        else:
            # use idx so we are sure we are in order.
            for idx in range(len(folder_contents)):
                expected_rec_filepath = file_path / f"shank_{idx}"
                self.data[str(idx)] = si.load_extractor(expected_rec_filepath)

    def get_folder_contents_and_shank_type(
        self, file_path: Path
    ) -> Tuple[List, Literal["single", "multi"]]:
        """"""
        folder_contents = list(file_path.glob("*"))
        folder_contents_names = [path_.stem for path_ in folder_contents]

        if "shank_0" in folder_contents_names:
            if not all(["shank_" in name for name in folder_contents_names]):
                raise RuntimeError(
                    f"There is a folder that does not begin with 'shank'"
                    f"in the preprocessed data folder at {file_path}. Please delete"
                    f"this folder - non-spikewrap files or folders should "
                    f"never be stored here."
                )

            return folder_contents, "multi"

        else:
            for name in [
                "properties",
                "binary",
                "probe",
                "provenance",
                "si_folder",
                "traces_cached_seg0",
            ]:
                if name not in folder_contents_names:
                    raise RuntimeError(
                        f"The file / folder {name} cannot be found in {file_path}.",
                        "There may be a problem when saving the preprocessed file.",
                        "Please contact spikewrap.",
                    )
            return folder_contents, "single"


def concatenate_preprocessed_run_recordings(
    recordings: List[PreprocessedRunRecording],
) -> PreprocessedRunRecording:
    breakpoint()

    # figure out data # TODO: ensure these are all in the same order? or at least all
    #  increasing
    expected_shank_idx = recordings[0].data.keys()

    # TODO: can we do this equality?
    for recording in recordings:
        assert first_recording_keys == recording.keys()

    for shank_idx in expected_shank_idx:
        breakpoint()
        expected_chan_idx = recordings[0].data[shank_idx].get_channel_ids()
        expected_sampling_freq = recordings[0].get_sampling_frequency()
        expected_dtype = recordings[0].get_dtype()  # TODO: check
        expected_group_num = recordings[0].get_property("group")
        for recording in recordings:
            assert recording.data[shank_idx].get_channel_ids() == expected_chan_idx
            assert (
                recording.data[shank_idx].get_sampling_frequency()
                == expected_sampling_freq
            )
            assert recording.data[shank_idx].get_dtype() == expected_dtype
            assert recording.data[shank_idx].get_property("group") == expected_group_num

    concatenated_data = {}
    for shank_idx in expected_shank_idx:
        [recording.data[shank_idx] for recording in recordings]
        # concat_shank_recordings = # USE SI
        concatenated_data[shank_idx] = concat_shank_recordings

    return PreprocessedRunRecording(data=concatenated_data)
