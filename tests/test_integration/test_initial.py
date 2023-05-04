import shutil
from pathlib import Path

import pytest

from swc_ephys.pipeline import full_pipeline

ON_HPC = False
import os
import shutil


class TestFirstEphys:
    def get_data_and_run_settings(self, multi_runs):
        """ """
        script_path = Path(os.path.dirname(os.path.realpath(__file__)))
        data_path = script_path.parent
        test_path = data_path / "data" / "steve_multi_run"
        sub_name = "1119617"
        run_names = "1119617_LSE1_shank12_cut"
        if multi_runs:
            run_names = [run_names] + [
                "1119617_posttest1_shank12_cut",
                "1119617_pretest1_shank12_cut",
            ]
        return test_path, sub_name, run_names

    def run_full_pipeline(
        self,
        multi_runs,
        use_existing_preprocessed_file=True,
        overwrite_existing_sorter_output=True,
        slurm_batch=False,
    ):
        base_path, sub_name, run_names = self.get_data_and_run_settings(multi_runs)

        output_path = base_path / "derivatives"

        if output_path.is_dir():
            print("CHECK THIS")
            shutil.rmtree(output_path)

        full_pipeline.run_full_pipeline(
            base_path,
            sub_name,
            run_names,
            config_name="test",
            sorter="kilosort2_5",
            use_existing_preprocessed_file=use_existing_preprocessed_file,
            overwrite_existing_sorter_output=overwrite_existing_sorter_output,
            slurm_batch=slurm_batch,
        )

        return output_path

    def test_single_run_local(self):
        self.run_full_pipeline(multi_runs=False)

    @pytest.mark.skipif(ON_HPC is False, reason="ON_HPC is false")
    def test_single_run_slurm(self):
        self.run_full_pipeline(multi_runs=False, slurm_batch=True)

    """
    def test_single_run_slurm():


    def test_single_run_slurm():


    def test_multi_run_slurm():


    def test_preprocessing_exists_error():


    def test_use_existing_preprocessing_errror():


    def test_sorter_exists_error():


    def test_overwrite_sorther():
    """
