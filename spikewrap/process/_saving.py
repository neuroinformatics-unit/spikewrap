import numpy as np


def save_sync_channel(recording, output_path, file_format):
    """

    """
    if file_format == "spikeglx":
        select_sync_recording = recording.select_channels([recording.get_channel_ids()[-1]])
        sync_data = select_sync_recording.get_traces()[:, 0]

        assert sync_data.size == select_sync_recording.get_num_samples()
        # assert np.unique(sync_data).size <= 2, "sync channel expected 0, 1"  # TODO: this assumption is probably wrong, but have a look

    elif file_format == "openephys":
        raise NotImplementedError()

    else:
        raise ValueError("File format type not recognised.")

    # Save the sync data
    output_path.mkdir(parents=True, exist_ok=True)
    full_output_filepath = output_path / "sync_channel.npy"  # TODO: use canonical
    np.save(full_output_filepath, sync_data)