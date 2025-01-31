from __future__ import annotations

from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from pathlib import Path

    from spikeinterface.core import BaseRecording

import numpy as np


def save_sync_channel(
    recording: BaseRecording,
    output_path: Path,
    file_format: Literal["spikeglx", "openephys"],
) -> None:
    """
    Save the sync channel data from a recording to a file.

    Extracts the sync channel data from the provided recording object and saves it
    as a `.npy` file in the specified output directory.

    Parameters
    ----------
    recording
        The recording object from which to extract the sync channel data.
    output_path
        The directory where the sync channel file will be saved.
    file_format
        The format of the recording file. Determines how the sync channel is extracted.

    Raises
    ------
    NotImplementedError
        If the `file_format` is "openephys", as it is not yet supported.
    ValueError
        If the provided `file_format` is not recognized.

    Notes
    -----
    - For "spikeglx" files, the sync channel is assumed to be the last channel
      in the recording.
    - The sync channel data is saved as `sync_channel.npy` in the specified
      `output_path` directory.
    - If the output directory does not exist, it is created automatically.
    """
    if file_format == "spikeglx":
        select_sync_recording = recording.select_channels(
            [recording.get_channel_ids()[-1]]
        )
        sync_data = select_sync_recording.get_traces()[:, 0]

        assert sync_data.size == select_sync_recording.get_num_samples()

    elif file_format == "openephys":
        raise NotImplementedError(
            "No test case has been found for sync channel with open ephys. Please get in contact."
        )

    else:
        raise ValueError("File format type not recognised.")

    # Save the sync data
    output_path.mkdir(parents=True, exist_ok=True)
    full_output_filepath = output_path / "sync_channel.npy"  # TODO: use canonical
    np.save(full_output_filepath, sync_data)
