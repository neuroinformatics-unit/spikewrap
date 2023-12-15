import numpy as np
import pytest
import spikeinterface.extractors as se
import spikeinterface.preprocessing as spre
from spikeinterface import (
    load_extractor,
    order_channels_by_depth,
)

from spikewrap.pipeline.load_data import load_data
from spikewrap.pipeline.preprocess import run_preprocessing
from spikewrap.utils import checks

from .base import BaseTest  # noqa

fast = True
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


class TestPreprocessingPipeline(BaseTest):
    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_smoke_preprocess_by_group(self, test_info):
        """ """
        self.remove_all_except_first_run_and_sessions(test_info)

        preprocess_data = load_data(*test_info[:3], data_format=DEFAULT_FORMAT)

        self.overwrite_test_data_with_larger_toy_example(preprocess_data)

        pp_steps = {"1": ("highpass_spatial_filter", {"n_channel_pad": 12})}

        with pytest.raises(AssertionError) as e:
            run_preprocessing(
                preprocess_data,
                pp_steps,
                handle_existing_data="fail_if_exists",
                preprocess_by_group=False,
            )

        assert "The recording contains multiple groups!" in str(e.value)

        run_preprocessing(
            preprocess_data,
            pp_steps,
            handle_existing_data="fail_if_exists",
            preprocess_by_group=True,
        )

    def overwrite_test_data_with_larger_toy_example(
        self, preprocess_data
    ):  # TODO: move to utils.
        """
        The small toy test file is loaded from disk to fully emulate the
        pipeline. However, in this case we need largest channels because
        `highpass_spatial_filter` cannot handle small channel recordings.

        The easiest way to do this, even if a bit hacky, is to simply
        overwrite the loaded recording with a new ordering. This is
        preferable to writing lots of toy example binaries.

        An offset is added to each sub / run recording so they
        are different when making numerical comparisons.
        """
        num_channels = 384  # must be even.

        # TODO: this is all a direct copy from `generate_test_data()`
        toy_recording, _ = se.toy_example(
            duration=[0.1], num_segments=1, num_channels=num_channels, num_units=2
        )
        two_shank_groupings = np.repeat([0, 1], int(num_channels / 2))
        toy_recording.set_property("group", two_shank_groupings)
        toy_recording.set_property(
            "inter_sample_shift", np.arange(num_channels) * 0.0001
        )

        for idx, (ses, run) in enumerate(preprocess_data.flat_sessions_and_runs()):
            preprocess_data[ses][run]["0-raw"] = spre.scale(
                toy_recording, offset=idx * 100
            )

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_preprocess_by_group_against_manually(self, test_info):
        """
        TODO: needs to be split up into multple tests. Currently it is
        slow so not worth it.
        # zscore is quite slow with aggregate channels.
        # TODO: need to test all runs?! no...
        # TODO: all tests will now fail due to chunk size change...
        # if chunk size is too small they will fail in future...

        # Run preprocessing per-shank through spikewrap with the preprocessing
        # steps defined in `pp_steps`.
        """
        self.remove_all_except_first_run_and_sessions(test_info)

        preprocess_data = load_data(*test_info[:3], data_format=DEFAULT_FORMAT)

        self.overwrite_test_data_with_larger_toy_example(preprocess_data)

        # zscore is quite slow with aggregate channels.
        pp_steps = {
            "1": ("phase_shift", {}),
            "2": ("bandpass_filter", {}),
            "3": ("common_reference", {}),
            "4": ("scale", {"gain": 2}),
            "5": ("highpass_spatial_filter", {}),
        }

        run_preprocessing(
            preprocess_data,
            pp_steps,
            handle_existing_data="overwrite",
            preprocess_by_group=True,
        )

        # Now, we take the base recording and re-apply all preprocessing steps
        # manually in SI, which we are sure is correct. This is done by
        # recursively reapplying the preprocessing steps to `test_recording`.
        run_name = list(preprocess_data["ses-001"].keys())[0]
        not_split_recording = preprocess_data["ses-001"][run_name]["0-raw"]
        split_recording = not_split_recording.split_by("group")

        test_recording = split_recording
        # fmt: off
        for pp_info, pp_dict_name, same_when_pp_together in zip(
            [[spre.phase_shift, {}], [spre.bandpass_filter, {}],          [spre.common_reference, {}],                          [spre.scale, {"gain": 2}],                                   [spre.highpass_spatial_filter, {}]],
            ["1-raw-phase_shift",    "2-raw-phase_shift-bandpass_filter", "3-raw-phase_shift-bandpass_filter-common_reference", "4-raw-phase_shift-bandpass_filter-common_reference-scale", "5-raw-phase_shift-bandpass_filter-common_reference-scale-highpass_spatial_filter"],
            [True,                    True,                                False,                                                False,                                                      False]
        ):
            # Apply the preprocessing directly to each shank
            pp_func, pp_kwargs = pp_info
            test_recording = {key: pp_func(recording, **pp_kwargs) for key, recording in test_recording.items()}

            # Get the preprocessed data from spikewrap
            spikewrap_preprocessed_recording = preprocess_data["ses-001"][run_name][pp_dict_name]

            # Check these match exactly
            assert np.array_equal(self.get_concatenated_data_from_split_recording(test_recording),
                                  spikewrap_preprocessed_recording.get_traces())

            # Check a version that is preprocessed without being split is not
            # the same as the split version.
            # Note cannot perform `highpass_spatial_filter` globally.
            if pp_func != spre.highpass_spatial_filter:
                not_split_recording = pp_func(not_split_recording)
                reorder = order_channels_by_depth(spikewrap_preprocessed_recording)[0]
                assert np.array_equal(not_split_recording.get_traces(),  spikewrap_preprocessed_recording.get_traces()[:, reorder]) is same_when_pp_together
        # fmt: on

        # Do a final quick check that the saved data matches the final
        # preprocessing step.
        output_path = (
            test_info[0]
            / "derivatives"
            / "spikewrap"
            / test_info[1]
            / "ses-001"
            / "ephys"
            / test_info[2]["ses-001"][0]
        )
        saved_data = load_extractor(output_path / "preprocessing" / "si_recording")

        stored_data = preprocess_data["ses-001"][run_name][
            "5-raw-phase_shift-bandpass_filter-common_reference-scale-highpass_spatial_filter"
        ]
        assert np.allclose(
            saved_data.get_traces(), stored_data.get_traces(), rtol=1, atol=1e-8
        )

    def get_concatenated_data_from_split_recording(self, split_recording):
        """ """
        all_data_list = []
        for rec in split_recording.values():
            all_data_list.append(rec.get_traces())

        all_data = np.hstack(all_data_list)
        return all_data

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_confidence_check_details(self, test_info):
        """ """
        self.remove_all_except_first_run_and_sessions(test_info)

        preprocess_data = load_data(*test_info[:3], data_format="spikeinterface")

        # zscore is quite slow with aggregate channels.
        pp_steps = {"1": ("common_reference", {"operator": "average"})}
        run_preprocessing(
            preprocess_data,
            pp_steps,
            handle_existing_data="overwrite",
            preprocess_by_group=True,
        )

        run_name = list(preprocess_data["ses-001"].keys())[0]
        base_recording = preprocess_data["ses-001"][run_name]["0-raw"]
        test_recording = base_recording.split_by("group")

        spikewrap_recording = preprocess_data["ses-001"][run_name][
            "1-raw-common_reference"
        ]
        spikewrap_data = spikewrap_recording.get_traces()

        groups = spikewrap_recording.get_property("group")

        all_channels_means = np.mean(base_recording.get_traces(), axis=1)

        for shank_idx, shank_rec in enumerate(test_recording.values()):
            test_data = shank_rec.get_traces()
            means = np.mean(test_data, axis=1)
            test_demeaned = test_data - means[:, np.newaxis]

            demeaned_wrong_mean = test_data - all_channels_means[:, np.newaxis]

            assert np.allclose(
                test_demeaned,
                spikewrap_data[:, np.where(groups == shank_idx)[0]],
                rtol=0,
                atol=1e-10,
            )
            assert not np.array_equal(
                demeaned_wrong_mean, spikewrap_data[:, np.where(groups == shank_idx)]
            )
