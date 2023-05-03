from pathlib import Path

from swc_ephys.pipeline.quality import quality_check

base_path = Path(
    Path(r"/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning")
)

sub_name = "1110925"
run_name = "1110925_test_shank1_cut"

output_path = base_path / "derivatives" / sub_name / f"{run_name}" / "preprocessed"

quality_check(output_path, sorter="kilosort2_5")
