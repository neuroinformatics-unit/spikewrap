import copy

import numpy as np
import pytest
from spikeinterface import load_extractor
from spikeinterface.preprocessing import (
    astype,
)

from spikewrap.pipeline.load_data import load_data

from .base import BaseTest  # noqa


class TestLoadData(BaseTest):
    @pytest.mark.parametrize(
        "test_info", ["spikeinterface"], indirect=True
    )  # TODO: naming now confusing between test format and SI format
    @pytest.mark.parametrize("mode", ["all_sessions_and_runs", "all_runs"])
    def test_all_keyword(self, test_info, mode):
        """
        Test the 'all' keyword for the `sessions_and_runs` dictionary which
        can take "all" in the sessions key or "all" as a run input. The 'only'
        keyword is not tested here.

        The two cases that are tested here are when session level is 'all'
        or when the run level for each session is 'all'. In either case,
        the data should be loaded as expected from the toy example file data.
        """
        base_path, sub_name, sessions_and_runs = test_info

        # Set the 'all' key on the sessions and runs
        if mode == "all_sessions_and_runs":
            new_sessions_and_runs = {"all": ["all"]}
        else:
            new_sessions_and_runs = copy.deepcopy(sessions_and_runs)
            for ses_name in sessions_and_runs.keys():
                new_sessions_and_runs[ses_name] = ["all"]

        preprocess_data = load_data(
            base_path, sub_name, new_sessions_and_runs, data_format="spikeinterface"
        )

        # Check the preprocess_data dict contains inputs
        # in the order that is expected
        assert list(preprocess_data.keys()) == ["ses-001", "ses-002", "ses-003"]

        for ses_name in preprocess_data.keys():
            assert list(preprocess_data[ses_name].keys()) == [
                f"{ses_name}_run-001",
                f"{ses_name}_run-002",
            ]

            for run in ["run-001", "run-002"]:
                run_name = f"{ses_name}_{run}"

                # for each run, check the expected run is loaded into
                # `preprocess_data`.
                test_run_data = load_extractor(
                    base_path
                    / "rawdata"
                    / sub_name
                    / ses_name
                    / "ephys"
                    / f"{ses_name}_{run}"
                )
                test_run_data = astype(test_run_data, np.float64)

                assert np.array_equal(
                    test_run_data.get_traces(),
                    preprocess_data[ses_name][run_name]["0-raw"].get_traces(),
                )

    @pytest.mark.parametrize("test_info", ["spikeinterface"], indirect=True)
    def test_all_keyword_session_all_run_normal(self, test_info):
        """
        This is a bad test in the case that sessions is "all"
        and runs is not "all". See issue #166 to resolve this.
        For the time being, on the current test set this will duplicate
        the runs for ses-001 to ses-002 and ses-003. The run names are
        different across sessions so this raises and error.
        """
        base_path, sub_name, sessions_and_runs = test_info

        new_sessions_and_runs = {"all": sessions_and_runs["ses-001"]}

        with pytest.raises(AssertionError) as e:
            load_data(
                base_path, sub_name, new_sessions_and_runs, data_format="spikeinterface"
            )

        assert "The run folder ses-001_run-001 cannot be found at file path" in str(
            e.value
        )

    @pytest.mark.parametrize("test_info", ["spikeinterface"], indirect=True)
    @pytest.mark.parametrize("session_or_run", ["session", "run"])
    def test_only_keyword(self, test_info, session_or_run):
        """
        Test that when the 'only' keyword is used in sessions and runs,
        either at the session level, then and error is raised if there is more
        than one session or run.
        """
        base_path, sub_name, sessions_and_runs = test_info

        if session_or_run == "session":
            new_sessions_and_runs = {"only": sessions_and_runs["ses-001"]}
        else:
            new_sessions_and_runs = {"ses-001": ["only"]}

        with pytest.raises(RuntimeError) as e:
            load_data(
                base_path, sub_name, new_sessions_and_runs, data_format="spikeinterface"
            )

        assert (
            f"contains more than one folder but the {session_or_run} keyword is set to 'only'."
            in str(e.value)
        )
