import shutil

import pytest

from spikewrap.utils.slurm import is_slurm_installed

from .base import BaseTest

CAN_SLURM = is_slurm_installed()


class TestSLURM(BaseTest):
    # TODO: cannot test the actual output.
    # can test recording at least.

    @pytest.mark.skipif(CAN_SLURM is False, reason="CAN_SLURM is false")
    @pytest.mark.parametrize(
        "concatenation", [(False, False)]  # , (False, True), (True, True)]
    )
    def test_full_pipeline_slurm(self, test_info, concatenation):
        concatenate_sessions, concatenate_runs = concatenation

        self.remove_all_except_first_run_and_sessions(test_info)  # TODO: REMVOE!

        base_path = test_info[0]

        self.clear_slurm_logs(base_path)

        self.run_full_pipeline(
            *test_info,
            concatenate_sessions=concatenate_sessions,
            concatenate_runs=concatenate_runs,
            slurm_batch={"wait": True},
        )

        self.check_slurm_log(base_path)

        self.check_correct_folders_exist(
            test_info, concatenate_sessions, concatenate_runs
        )

    def check_slurm_log(self, base_path):
        """ """
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
        """ """
        slurm_path = base_path / "slurm_logs"
        [shutil.rmtree(path_) for path_ in slurm_path.glob("*-*-*_*-*-*")]
