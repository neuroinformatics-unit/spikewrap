import shutil

import pytest

from spikewrap.utils import checks
from spikewrap.utils.slurm import is_slurm_installed

from .base import BaseTest  # noqa

CAN_SLURM = is_slurm_installed()

fast = True  # TOOD: if slow this will still use fast fixture - fix this!
# TODO: REMOVE DUPLICATION
if fast:
    DEFAULT_SORTER = "mountainsort5"
    DEFAULT_FORMAT = "spikeinterface"  # TODO: make explicit this is fast
    DEFAULT_PIPELINE = "fast_test_pipeline"

else:
    if not (checks.check_virtual_machine() and checks.check_cuda()):
        raise RuntimeError("Need NVIDIA GPU for run kilosort for slow tests")
    DEFAULT_SORTER = "kilosort2_5"
    DEFAULT_FORMAT = "spikeglx"
    DEFAULT_PIPELINE = "test_default"


class TestSLURM(BaseTest):
    # TODO: cannot test the actual output.
    # can test recording at least.

    @pytest.mark.skipif(CAN_SLURM is False, reason="CAN_SLURM is false")
    @pytest.mark.parametrize(
        "concatenation", [(False, False), (False, True), (True, True)]
    )
    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_full_pipeline_slurm(self, test_info, concatenation):
        concatenate_sessions, concatenate_runs = concatenation

        self.remove_all_except_first_run_and_sessions(test_info)  # TODO: REMVOE!

        base_path = test_info[0]

        self.clear_slurm_logs(base_path)

        self.run_full_pipeline(
            *test_info,
            data_format=DEFAULT_FORMAT,
            sorter=DEFAULT_SORTER,
            concatenate_sessions=concatenate_sessions,
            concatenate_runs=concatenate_runs,
            slurm_batch={"wait": True},
        )

        self.check_slurm_log(base_path)

        self.check_correct_folders_exist(
            test_info,
            concatenate_sessions,
            concatenate_runs,
            DEFAULT_SORTER,
        )

    def check_slurm_log(self, base_path):
        """ """
        slurm_run = base_path.glob("slurm_logs/*/*log.out")
        slurm_run = list(slurm_run)[0]

        with open(slurm_run, "r") as log:
            log_output = log.readlines()

        log_output = " ".join(log_output)

        assert "Saving waveforms to" in log_output
        assert "Quality metrics saved to" in log_output
        assert "Job completed successfully" in log_output

    def clear_slurm_logs(self, base_path):
        """ """
        slurm_path = base_path / "slurm_logs"
        [shutil.rmtree(path_) for path_ in slurm_path.glob("*-*-*_*-*-*")]
