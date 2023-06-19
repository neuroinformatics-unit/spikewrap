from pathlib import Path

from swc_ephys.pipeline.postprocess import run_postprocess

base_path = Path(
    Path(r"/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning")
)

sub_name = "1110925"
run_name = "1110925_test_shank1_cut"

output_path = base_path / "derivatives" / sub_name / f"{run_name}" / "preprocessed"

run_postprocess(output_path, sorter="kilosort2_5")
