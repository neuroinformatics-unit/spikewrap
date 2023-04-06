"""
"""
from preprocess import preprocess
from sort import run_sorting
import numpy as np
from pathlib import Path
from quality import quality_check

base_path = Path(r"/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning")
sub_name = "1110925"
run_name = "1110925_test_shank1"

output_path = base_path / "derivatives" / sub_name / f"{run_name}_g0"

quality_check(output_path,
              sorter="kilosort2_5")

