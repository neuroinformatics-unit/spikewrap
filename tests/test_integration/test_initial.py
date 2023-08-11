"""
TODO: these tests don't check any output, only that things run without error
"""
import os
import shutil
from pathlib import Path

import pytest

from spikewrap.pipeline import full_pipeline, preprocess
from spikewrap.pipeline.full_pipeline import get_configs
from spikewrap.pipeline.load_data import load_data
from spikewrap.utils.slurm import is_slurm_installed

CAN_SLURM = is_slurm_installed()


class TestFirstEphys:
    @pytest.fixture(scope="class")
    def base_path(self):
        script_path = Path(os.path.dirname(os.path.realpath(__file__)))
        data_path = script_path.parent
        base_path = data_path / "data" / "steve_multi_run"
        return base_path

    @pytest.fixture(scope="function")
    def test_info(self, base_path, request):
        """ """
        if not hasattr(request, "param"):
            mode = "time-short"
        else:
            mode = request.param

        base_path = base_path / mode

        sub_name = "1119617"
        run_names = [
            "1119617_LSE1_shank12_g0",
            "1119617_posttest1_shank12_g0",
            "1119617_pretest1_shank12_g0",
        ]

        output_path = base_path / "derivatives"
        if output_path.is_dir():
            shutil.rmtree(output_path)

        yield [base_path, sub_name, run_names]

        if output_path.is_dir():
            shutil.rmtree(output_path)

    def run_full_pipeline(
        self,
        base_path,
        sub_name,
        run_names,
        sorter="kilosort2_5",
        concat_for_sorting=False,
        existing_preprocessed_data="fail_if_exists",
        existing_sorting_output="fail_if_exists",
        slurm_batch=False,
    ):
        full_pipeline.run_full_pipeline(
            base_path,
            sub_name,
            run_names,
            config_name="default",
            sorter=sorter,
            concat_for_sorting=concat_for_sorting,
            existing_preprocessed_data=existing_preprocessed_data,
            existing_sorting_output=existing_sorting_output,
            overwrite_postprocessing=True,
            slurm_batch=slurm_batch,
        )

    @pytest.mark.parametrize("test_info", ["time-tiny"], indirect=True)
    def test_preprocessing_options_with_small_file(self, test_info):
        """"""
        pp_steps, __, __ = get_configs("test_pp_small_file")

        preprocess_data = load_data(*test_info[:3], data_format="spikeglx")

        for run_name in preprocess_data.run_names:
            preprocess_data = preprocess.preprocess(
                preprocess_data, run_name, pp_steps, verbose=True
            )

            preprocess_data.save_preprocessed_data(run_name, overwrite=True)

    def test_preprocessing_options_with_large_file(self, test_info):
        """
        Some preprocessing steps do not ru non the  short file because
        of issues with chunk size. The ones that didn't work
        are run here on a larger file.
        """
        pp_steps, __, __ = get_configs("test_pp_large_file")

        preprocess_data = load_data(*test_info[:3])

        for run_name in preprocess_data.run_names:
            preprocess_data = preprocess.preprocess(
                preprocess_data, run_name, pp_steps, verbose=True
            )
            preprocess_data.save_preprocessed_data(run_name, overwrite=True)

    @pytest.mark.parametrize(
        "sorter",
        [
            #     "kilosort2",
            #    "kilosort2_5",
            #   "kilosort3",
            #  "mountainsort5",
            "spykingcircus",
            #  "tridesclous",
        ],
    )
    def test_single_run_local__(self, test_info, sorter):
        test_info[2] = test_info[2][0]
        self.run_full_pipeline(*test_info, sorter=sorter, concat_for_sorting=False)

    def test_single_run_local_overwrite(self, test_info):
        test_info[2] = test_info[2][0]

        self.run_full_pipeline(*test_info)

        self.run_full_pipeline(
            *test_info,
            existing_preprocessed_data="overwrite",
            existing_sorting_output="overwrite",
        )

        with pytest.raises(BaseException) as e:
            self.run_full_pipeline(
                *test_info, existing_preprocessed_data="fail_if_exists"
            )

        assert "To overwrite, set 'existing_preprocessed_data' to 'overwrite'" in str(
            e.value
        )

    def test_multi_run_local(self, test_info):
        test_info[2] = test_info[2][0]

        self.run_full_pipeline(*test_info)

    @pytest.mark.skipif(CAN_SLURM is False, reason="CAN_SLURM is false")
    def test_single_run_slurm(self, test_info):
        base_path = test_info[0]

        test_info[2] = test_info[2][0]

        self.clear_slurm_logs(base_path)

        self.run_full_pipeline(*test_info, slurm_batch={"wait": True})

        self.check_slurm_log(base_path)

    @pytest.mark.skipif(CAN_SLURM is False, reason="CAN_SLURM is false")
    def test_multi_run_slurm(self, test_info):
        base_path = test_info[0]

        self.clear_slurm_logs(base_path)

        self.run_full_pipeline(*test_info, slurm_batch={"wait": True})

        self.check_slurm_log(base_path)

    def check_slurm_log(self, base_path):
        slurm_run = base_path.glob("slurm_logs/*/*log.out")
        slurm_run = list(slurm_run)[0]

        with open(slurm_run, "r") as log:
            log_output = log.readlines()

        log_output = " ".join(log_output)

        assert "Stopping container" in log_output
        assert "Saving waveforms to" in log_output
        assert "Quality metrics saved to" in log_output
        assert "Job completed successfully" in log_output

    def clear_slurm_logs(self, base_path):
        slurm_path = base_path / "slurm_logs"
        [shutil.rmtree(path_) for path_ in slurm_path.glob("*-*-*_*-*-*")]

    def test_preprocessing_exists_error(self):
        raise NotImplementedError

    def test_use_existing_preprocessing_errror(self):
        raise NotImplementedError

    def test_sorter_exists_error(self):
        raise NotImplementedError

    def test_overwrite_sorter(self):
        raise NotImplementedError

    def test_overwrite_waveforms(self):
        raise NotImplementedError

    def test_overwrite_postprocessing(self):
        raise NotImplementedError

    def test_sorting_only_local(self):
        raise NotImplementedError

    def test_sorting_only_slumr(self):
        raise NotImplementedError
