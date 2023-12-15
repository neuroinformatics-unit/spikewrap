from pathlib import Path

from spikeinterface import generate_ground_truth_recording

print("Starting...")

sessions_and_runs = {"ses-001": ["ses-001_run-001", "ses-001_run-002"]}

sub = "sub-001_type-multiseg"

base_path = Path(__file__).parent.resolve() / "rawdata"

for ses in sessions_and_runs.keys():
    for run in sessions_and_runs[ses]:
        num_channels = 384
        # if seg too small will error
        # TODO: issue on SI default durations as list on generate
        recording, _ = generate_ground_truth_recording(
            durations=[0.1, 0.1, 0.1], num_channels=num_channels, num_units=2
        )

        output_path = base_path / sub / ses / "ephys" / run

        recording.save(folder=output_path, chunk_size=1000000, overwrite=True)
