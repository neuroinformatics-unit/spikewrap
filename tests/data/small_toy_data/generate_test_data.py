from pathlib import Path

import numpy as np
import spikeinterface.extractors as se
import spikeinterface.preprocessing as spre

print("Starting...")

sessions_and_runs = {
    "ses-001": ["ses-001_run-001", "ses-001_run-002"],
    "ses-002": ["ses-002_run-001", "ses-002_run-002"],
    "ses-003": ["ses-003_run-001", "ses-003_run-002"],
}

if False:
    from spikewrap.pipeline.preprocess import run_preprocessing

    sub_name = "sub-001_type-test"
    base_path = Path(__file__).parent.resolve()

    from spikewrap.pipeline.load_data import load_data

    preprocess_data = load_data(
        base_path, sub_name, sessions_and_runs, "spikeinterface"
    )

    run_preprocessing(
        preprocess_data,
        "default",
        handle_existing_data="overwrite",
        slurm_batch=False,
        log=False,
    )  # TODO: use config_name for all funcs.


# if False:

sub = "sub-001_type-test"
base_path = Path(__file__).parent.resolve() / "rawdata"

for ses in sessions_and_runs.keys():
    for run in sessions_and_runs[ses]:
        num_channels = 16
        recording, _ = se.toy_example(
            duration=[0.05], num_segments=1, num_channels=num_channels, num_units=2
        )
        four_shank_groupings = np.repeat([0, 1, 2, 3], 4)
        recording.set_property("group", four_shank_groupings)
        recording.set_property("inter_sample_shift", np.arange(16) * 0.0001)

        recording._main_ids = np.array(
            [f"imec0.ap#AP{i}" for i in range(num_channels)]
        )  # for consistency with spikeglx dataset TODO this is a hack

        recording = spre.scale(recording, gain=50, offset=20)

        output_path = base_path / sub / ses / "ephys" / run

        recording.save(folder=output_path, chunk_size=1000000)

# shifted_recording = spre.phase_shift(recording)
# filtered_recording = spre.bandpass_filter(recording)
# referenced_recording = spre.common_reference(filtered_recording)
# run_sorter("mountainsort5", referenced_recording, remove_existing_folder=True, whiten=False)
