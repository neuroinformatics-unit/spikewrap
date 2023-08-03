from pathlib import Path

from spikewrap.pipeline.postprocess import run_postprocess

base_path = Path(
    r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short"
)
# TODO: why is this taking the preprocessed path? isn't sorting more intuitive? or top level? think...
sub_name = "1119617"
run_name = "1119617_LSE1_shank12_posttest1_pretest1"

preprocessing_path = (
    base_path / "derivatives" / sub_name / f"{run_name}" / "preprocessed"
)

run_postprocess(
    preprocessing_path,
    sorter="kilosort2_5",
    existing_waveform_data="overwrite",
    postprocessing_to_run="all",
)
