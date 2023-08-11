from pathlib import Path

from spikewrap.pipeline.postprocess import run_postprocess

base_path = Path(
    r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/test_data/steve_multi_run/1119617/time-short"
)
sub_name = "1119617"
run_name = "1119617_LSE1_shank12_posttest1_pretest1"

sorting_path = (
    base_path
    / "derivatives"
    / sub_name
    / "1119617-sorting-concat"
    / f"{run_name}"
    / "mountainsort5"
    / "sorting"
)

run_postprocess(
    sorting_path,
    existing_waveform_data="overwrite",
    postprocessing_to_run="all",
)
