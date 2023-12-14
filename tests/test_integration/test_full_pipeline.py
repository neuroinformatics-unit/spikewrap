import platform

import numpy as np
import pytest
import spikeinterface as si
import spikeinterface.extractors as se
from spikeinterface import concatenate_recordings
from spikeinterface.preprocessing import (
    astype,
    bandpass_filter,
    common_reference,
    phase_shift,
)

from spikewrap.data_classes.postprocessing import load_saved_sorting_output
from spikewrap.pipeline import full_pipeline, preprocess
from spikewrap.pipeline.load_data import load_data
from spikewrap.utils import checks, utils

from .base import BaseTest  # noqa

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


class TestFullPipeline(BaseTest):
    # TODO: naming now confusing between test format and SI format
    @pytest.mark.parametrize("test_info", ["multi_segment"], indirect=True)
    def test_multi_segment(self, test_info):
        with pytest.raises(ValueError) as e:
            load_data(*test_info[:3], data_format="spikeinterface")

        assert (
            str(e.value)
            == "Multi-segment recordings are not currently supported. Please get in contact!"
        )

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_preprocessing_options_1(self, test_info):
        """
        A very basic test to run all preprocessing and check now error occurs.
        Not all preprocessing steps are compatible, so other steps are tested in
        `test_preprocessing_options_2`.
        """
        self.remove_all_except_first_run_and_sessions(test_info)

        pp_steps, __, __ = full_pipeline.get_configs("test_preprocessing_1")

        preprocess_data = load_data(*test_info[:3], data_format=DEFAULT_FORMAT)

        for ses_name, run_name in preprocess_data.flat_sessions_and_runs():
            preprocess._fill_run_data_with_preprocessed_recording(
                preprocess_data,
                ses_name,
                run_name,
                pp_steps,
                preprocess_per_shank=False,
            )
            preprocess_data.save_preprocessed_data(ses_name, run_name, overwrite=True)

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_preprocessing_options_2(self, test_info):
        """
        see `test_preprocessing_options_1()`
        """
        self.remove_all_except_first_run_and_sessions(test_info)

        pp_steps, __, __ = full_pipeline.get_configs("test_preprocessing_2")

        preprocess_data = load_data(*test_info[:3], data_format=DEFAULT_FORMAT)

        for ses_name, run_name in preprocess_data.flat_sessions_and_runs():
            preprocess._fill_run_data_with_preprocessed_recording(
                preprocess_data,
                ses_name,
                run_name,
                pp_steps,
                preprocess_per_shank=False,
            )
            preprocess_data.save_preprocessed_data(ses_name, run_name, overwrite=True)

    # --------------------------------------------------------------------------------------
    # Full Slow Tests
    # --------------------------------------------------------------------------------------

    @pytest.mark.skipif(
        "fast is True", reason="'fast' must be set to `False` to run all sorters."
    )
    @pytest.mark.parametrize(
        "sorter",
        [
            "kilosort2",
            "kilosort2_5",
            "kilosort3",
            "mountainsort5",
            "tridesclous",
        ],
    )
    def test_no_concatenation_all_sorters_single_run(self, test_info, sorter):
        """
        For every supported sorter, run the full pipeline for a single
        session and run, and check preprocessing, sorting and waveforms.
        """
        self.remove_all_except_first_run_and_sessions(test_info)

        loaded_data, sorting_data = self.run_full_pipeline(
            *test_info,
            sorter=sorter,
            concatenate_sessions=False,
            concatenate_runs=False,
        )

        self.check_correct_folders_exist(test_info, False, False, sorter)
        self.check_no_concat_results(test_info, loaded_data, sorting_data, sorter)

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_no_concatenation_single_run(self, test_info):
        """
        Run the full pipeline for a single
        session and run, and check preprocessing, sorting and waveforms.
        """
        self.remove_all_except_first_run_and_sessions(test_info)

        loaded_data, sorting_data = self.run_full_pipeline(
            *test_info,
            data_format=DEFAULT_FORMAT,
            sorter=DEFAULT_SORTER,
            concatenate_sessions=False,
            concatenate_runs=False,
        )

        self.check_correct_folders_exist(test_info, False, False, DEFAULT_SORTER)
        self.check_no_concat_results(
            test_info, loaded_data, sorting_data, DEFAULT_SORTER
        )

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_no_concatenation_multiple_runs(self, test_info):
        """
        For DEFAULT_SORTER, check `full_pipeline` across multiple sessions
        and runs without concatenation.
        """
        loaded_data, sorting_data = self.run_full_pipeline(
            *test_info,
            data_format=DEFAULT_FORMAT,
            concatenate_sessions=False,
            concatenate_runs=False,
            sorter=DEFAULT_SORTER,
        )

        self.check_correct_folders_exist(test_info, False, False, DEFAULT_SORTER)

        self.check_correct_folders_exist(test_info, False, False, DEFAULT_SORTER)
        self.check_no_concat_results(test_info, loaded_data, sorting_data)

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_concatenate_runs_but_not_sessions(self, test_info):
        """
        For DEFAULT_SORTER, check `full_pipeline` across multiple sessions
        concatenating runs, but not sessions. This results in a single
        sorting output per-session consisting of all concatenated
        runs for that session to test.
        """
        loaded_data, sorting_data = self.run_full_pipeline(
            *test_info,
            data_format=DEFAULT_FORMAT,
            concatenate_sessions=False,
            concatenate_runs=True,
            sorter=DEFAULT_SORTER,
        )

        self.check_correct_folders_exist(test_info, False, True, DEFAULT_SORTER)
        self.check_concatenate_runs_but_not_sessions(
            test_info, loaded_data, sorting_data
        )

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_concatenate_sessions_and_runs(self, test_info):
        """
        For DEFAULT_SORTER, check `full_pipeline` across multiple sessions
        concatenating runs and sessions. This will lead to a single
        sorting output (consisting of all sessions / runs concatenated) to test.
        """
        loaded_data, sorting_data = self.run_full_pipeline(
            *test_info,
            data_format=DEFAULT_FORMAT,
            concatenate_sessions=True,
            concatenate_runs=True,
            sorter=DEFAULT_SORTER,
        )

        self.check_correct_folders_exist(test_info, True, True, DEFAULT_SORTER)
        self.check_concatenate_sessions_and_runs(test_info, loaded_data, sorting_data)

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_ses_concat_no_run_concat(self, test_info):
        """
        Check that an error is raised when `concatenate_sessions` is `True`
        but `concatenate_runs` is `False`. This combination is not allowed
        because runs must be concatenated in order to concatenate across sessions.
        """
        with pytest.raises(ValueError) as e:
            self.run_full_pipeline(
                *test_info,
                data_format=DEFAULT_FORMAT,
                concatenate_sessions=True,
                concatenate_runs=False,
                sorter=DEFAULT_SORTER,
            )

        assert (
            str(e.value)
            == "`concatenate_runs` must be `True` if `concatenate_sessions` is `True`"
        )

    @pytest.mark.parametrize("test_info", [DEFAULT_FORMAT], indirect=True)
    def test_existing_output_settings(self, test_info):
        """
        In spikewrap existing preprocessed and sorting output data is
        handled with options `fail_if_exists`, `skip_if_exists` or
        `overwrite`. Check that the expected behaviour occurs when each of
        these options is set.

        `overwrite_postprocessing` is either `True` (overwrite the entire
        postprocessing output) or `False` (error if exists). This is because
        it  would be misleading to re-run the sorting but keep old postprocessing
        output in the folder.
        """
        self.remove_all_except_first_run_and_sessions(test_info)
        ses_name = list(test_info[2].keys())[0]
        run_name = test_info[2][ses_name][0]

        # Run the first time
        self.run_full_pipeline(
            *test_info,
            data_format=DEFAULT_FORMAT,
            existing_preprocessed_data="fail_if_exists",
            existing_sorting_output="fail_if_exists",
            overwrite_postprocessing=False,
            sorter=DEFAULT_SORTER,
        )

        # Test outputs are overwritten if `overwrite` set.
        file_paths = self.write_an_empty_file_in_outputs(test_info, ses_name, run_name)

        self.run_full_pipeline(
            *test_info,
            data_format=DEFAULT_FORMAT,
            existing_preprocessed_data="overwrite",
            existing_sorting_output="overwrite",
            overwrite_postprocessing=True,
            sorter=DEFAULT_SORTER,
        )

        for path_ in file_paths:
            assert not path_.is_file()

        file_paths = self.write_an_empty_file_in_outputs(test_info, ses_name, run_name)

        # Test outputs are not overwritten if `skip_if_exists`.
        # Postprocessing is always deleted
        self.run_full_pipeline(
            *test_info,
            data_format=DEFAULT_FORMAT,
            existing_preprocessed_data="skip_if_exists",
            existing_sorting_output="skip_if_exists",
            overwrite_postprocessing=True,
            sorter=DEFAULT_SORTER,
        )
        for path_ in file_paths:
            if "postprocessing" not in path_.as_posix():
                assert path_.is_file()

        # Test an error is raised for existing preprocessing.
        with pytest.raises(BaseException) as e:
            self.run_full_pipeline(
                *test_info,
                data_format=DEFAULT_FORMAT,
                existing_preprocessed_data="fail_if_exists",
                existing_sorting_output="skip_if_exists",
                overwrite_postprocessing=True,
                sorter=DEFAULT_SORTER,
            )

        assert "To overwrite, set 'existing_preprocessed_data' to 'overwrite'" in str(
            e.value
        )

        if platform.system() != "Windows":
            # This is failing on windows because `overwrite_postprocessing=False` asserts
            # and there is an open link to the preprocessed binary data somewhere
            # that is not closed, only on Windows for some reason.

            # Test an error is raised for existing sorting.
            with pytest.raises(BaseException) as e:
                self.run_full_pipeline(
                    *test_info,
                    data_format=DEFAULT_FORMAT,
                    existing_preprocessed_data="skip_if_exists",
                    existing_sorting_output="fail_if_exists",
                    overwrite_postprocessing=True,
                    sorter=DEFAULT_SORTER,
                )

            assert "Sorting output already exists at" in str(e.value)

            # Test an error is raised for existing postprocessing.
            with pytest.raises(BaseException) as e:
                self.run_full_pipeline(
                    *test_info,
                    data_format=DEFAULT_FORMAT,
                    existing_preprocessed_data="skip_if_exists",
                    existing_sorting_output="skip_if_exists",
                    overwrite_postprocessing=False,
                    sorter=DEFAULT_SORTER,
                )

            assert "Postprocessing output already exists at" in str(e.value)

    # ----------------------------------------------------------------------------------
    # Checkers
    # ----------------------------------------------------------------------------------

    def check_no_concat_results(
        self, test_info, loaded_data, sorting_data, sorter=DEFAULT_SORTER
    ):
        """
        After `full_pipeline` is run, check the preprocessing, sorting and postprocessing
        output is as expected.

        Preprocessing is always run per-session, and in this instance (no concatenation)
        sorting and postprocessing are performed per-session. Therefore, iterate
        across all runs and sessions and for each, preprocess these directly in
        SI in the test environemnt and check that:

        1) That the raw data in the loaded_data` class matches that loaded by Si
        in the test environment.
        2) The preprocessed data in the `sorting_data` (e.g. `sorting_data[ses_name][run_name]`)
        matches the test data.
        3) That waveforms are extracted from  the correct (i.e. fully preprocerssed)
        data.

        In this case, no recording.dat file is written because SI feeds the existing
        preprocessed binary into the sorter.

        Note
        ----
        It is not currently possible to test the preprocessed data on the `loaded_data`
        class, due to the chunking issue described in `check_recordings_are_the_same()`.
        """
        base_path, sub_name, sessions_and_runs = test_info

        for ses_name in sessions_and_runs.keys():
            for run_name in sessions_and_runs[ses_name]:
                (
                    test_rawdata,
                    test_preprocessed,
                ) = self.get_test_rawdata_and_preprocessed_data(
                    base_path, sub_name, ses_name, run_name
                )

                pp_key = self.get_pp_key(loaded_data[ses_name][run_name])
                self.check_recordings_are_the_same(
                    loaded_data[ses_name][run_name]["0-raw"], test_rawdata
                )
                self.check_recordings_are_the_same(
                    loaded_data[ses_name][run_name][pp_key], test_preprocessed
                )

                # sorting is loaded from binary data which is stored in the
                # original dtype
                test_preprocessed = astype(
                    test_preprocessed, sorting_data[ses_name][run_name].dtype
                )  # TODO: TIDY

                self.check_recordings_are_the_same(
                    sorting_data[ses_name][run_name], test_preprocessed
                )

                paths = self.get_output_paths(
                    test_info, ses_name, run_name, sorter=sorter
                )

                self.check_waveforms(
                    paths["sorter_output"],
                    paths["postprocessing"],
                    recs_to_test=[
                        sorting_data[ses_name][run_name],
                    ],
                    sorter=sorter,
                )

    def check_concatenate_runs_but_not_sessions(
        self, test_info, loaded_data, sorting_data
    ):
        """
        Similar to `check_no_concat_results()`, however now test with
        `concatenate_runs=True`, which for each session will concatante the
        preprocessed runs before sorting.

        This necessitates as compared to `check_no_concat_results()`
        is that the test preprocessed data is first concatenated across runs
        before further checks.

        In this case, spikeinterface writes a `recording.dat` file which is
        also tested.
        """
        base_path, sub_name, sessions_and_runs = test_info

        for ses_name in sessions_and_runs.keys():
            # For each run, check the preprocessed data and store it
            # for later concatenation
            all_runs = []
            for run_name in sessions_and_runs[ses_name]:
                (
                    test_rawdata,
                    test_preprocessed,
                ) = self.get_test_rawdata_and_preprocessed_data(
                    base_path, sub_name, ses_name, run_name
                )

                self.check_recordings_are_the_same(
                    loaded_data[ses_name][run_name]["0-raw"], test_rawdata
                )
                pp_key = self.get_pp_key(loaded_data[ses_name][run_name])
                self.check_recordings_are_the_same(
                    loaded_data[ses_name][run_name][pp_key], test_preprocessed
                )

                assert run_name not in sorting_data[ses_name]

                all_runs.append(test_preprocessed)

            assert len(sorting_data[ses_name]) == 1
            concat_run_name = list(sorting_data[ses_name].keys())[0]
            sorting_data_pp_run = sorting_data[ses_name][concat_run_name]
            data_type = sorting_data_pp_run.dtype

            # Concatenate all runs used for testing, and check they
            # match the `sorting_data` preprocessed runs.
            test_concat_runs = concatenate_recordings(all_runs)

            # Convert to int16 for sorting and loaded file checks,
            # as dtype converted to original dtype on file writing.
            test_concat_runs = astype(test_concat_runs, data_type)

            self.check_recordings_are_the_same(
                sorting_data_pp_run, test_concat_runs, n_split=2
            )

            # Load the recording.dat and check it matches the expected data.
            # Finally, check the waveforms match the preprocessed data.
            paths = self.get_output_paths(
                test_info, ses_name, concat_run_name, concatenate_runs=True
            )

            if "kilosort" in sorting_data.sorter:
                saved_recording = si.read_binary(
                    paths["recording_dat"],
                    sampling_frequency=sorting_data_pp_run.get_sampling_frequency(),
                    dtype=data_type,
                    num_channels=sorting_data_pp_run.get_num_channels(),
                )
                self.check_recordings_are_the_same(
                    saved_recording, test_concat_runs, n_split=2
                )

            self.check_waveforms(
                paths["sorter_output"],
                paths["postprocessing"],
                recs_to_test=[sorting_data[ses_name][concat_run_name]],
            )

    def check_concatenate_sessions_and_runs(self, test_info, loaded_data, sorting_data):
        """
        Similar to `check_no_concat_results()` and `check_concatenate_runs_but_not_sessions()`,
        but now we are checking when `concatenate_sessions=True` and `concatenate_runs=`True`.
        This requires testing preprocessing per-run, and a single output for
        sorting and postprocessing that consists of all runs concatenated together.

        In this case, spikeinterface writes a `recording.dat` file which is
        also tested.
        """
        base_path, sub_name, sessions_and_runs = test_info

        all_ses_and_runs = []
        for ses_name in sessions_and_runs.keys():
            for run_name in sessions_and_runs[ses_name]:
                (
                    test_rawdata,
                    test_preprocessed,
                ) = self.get_test_rawdata_and_preprocessed_data(
                    base_path, sub_name, ses_name, run_name
                )

                last_key = list(loaded_data[ses_name][run_name].keys())[-1]
                self.check_recordings_are_the_same(
                    loaded_data[ses_name][run_name]["0-raw"], test_rawdata
                )
                self.check_recordings_are_the_same(
                    loaded_data[ses_name][run_name][last_key], test_preprocessed
                )

                all_ses_and_runs.append(test_preprocessed)

        assert len(sorting_data) == 1
        concat_ses_name = list(sorting_data.keys())[0]
        sorted_data_concat_all = sorting_data[concat_ses_name]
        data_type = sorting_data[concat_ses_name].dtype

        # Concatenate every session's runs together, and check this
        # test data matches the data stored in `sorted_data`, the recording.dat
        # and that all waveforms match preprocessed data.
        test_concat_all = concatenate_recordings(all_ses_and_runs)

        # Convert to int16 for sorting and load data test are
        # dtype is converted to original dtype on file writing.
        test_concat_all = astype(test_concat_all, data_type)

        paths = self.get_output_paths(
            test_info,
            ses_name=concat_ses_name,
            run_name=None,
            concatenate_sessions=True,
            concatenate_runs=True,
        )

        self.check_recordings_are_the_same(
            sorted_data_concat_all, test_concat_all, n_split=6
        )

        if "kilosort" in sorting_data.sorter:
            saved_recording = si.read_binary(
                paths["recording_dat"],
                sampling_frequency=sorted_data_concat_all.get_sampling_frequency(),
                dtype=data_type,
                num_channels=sorted_data_concat_all.get_num_channels(),
            )
            self.check_recordings_are_the_same(
                saved_recording, test_concat_all, n_split=6
            )

        self.check_waveforms(
            paths["sorter_output"],
            paths["postprocessing"],
            recs_to_test=[sorting_data[concat_ses_name]],
        )

    def check_recordings_are_the_same(self, rec_1, rec_2, n_split=1):
        """
        Check that two SI recording objects are exactly the same. When the
        memory is large enoguh such that the chunk size is larger than the
        recording length (usual case, this is OK). However, see below
        for notes on the case when the `get_traces()` call is performed in
        chunks, which this function also handles.

        When storing to binary, the data is chunked (if does not all fit
        into memory), preprocessed and written to disk).  When loading the stored
        binary file, these filter edge effects will be different
        to those from a raw-data recording that is preprocessed and `get_traces()`
        is called on the fly. The only way it will match exactly is when the
        chunk size extracted with `get_traces()` matches that used for writing
        the binary file.

        TODO
        ----
        Make an SI issue as it would be nicer to carry the filter over
        when chunking during writing the binary file.
        """
        assert rec_1.get_num_samples() == rec_2.get_num_samples()
        assert rec_1.get_num_segments() == rec_2.get_num_segments()
        assert rec_1.get_sampling_frequency() == rec_2.get_sampling_frequency()

        chunk = utils.get_default_chunk_size(rec_1)
        num_samples_split = rec_1.get_num_samples() / n_split
        quotient = num_samples_split // chunk
        bounds = np.r_[np.arange(quotient + 1) * chunk, num_samples_split].astype(int)

        for split in np.arange(n_split):
            offset = int(num_samples_split * split)

            for start, end in zip(bounds[:-1], bounds[1:]):
                start += offset
                end += offset
                assert np.allclose(
                    rec_1.get_traces(
                        start_frame=start, end_frame=end, return_scaled=False
                    ),
                    rec_2.get_traces(
                        start_frame=start, end_frame=end, return_scaled=False
                    ),
                    rtol=0,
                    atol=1e-10,
                )

    def check_waveforms(
        self,
        sorter_output_path,
        postprocessing_path,
        recs_to_test,
        sorter=DEFAULT_SORTER,
    ):
        """
        Check the waveform output matches that expected from the test-preprocessed
        and sorted data. The waveforms output is loaded, as is the sorting output.
        For all waveforms, get the spike times from the sorting output and
        index out the corresponding data from the spikeinterface recording
        objects passed in `recs_to_test` (i.e. the preprocessed data).
        """
        waveforms_folder = postprocessing_path / "waveforms"

        sorting = load_saved_sorting_output(sorter_output_path, sorter)

        sorting = sorting.remove_empty_units()

        waveforms = si.load_waveforms(postprocessing_path)

        for unit_idx in sorting.get_non_empty_unit_ids():
            times, indexes = self.get_times_of_waveform_spikes(
                waveforms, sorting, unit_idx
            )
            first_unit_waveforms = np.load(
                waveforms_folder / f"waveforms_{unit_idx}.npy"
            )

            _, _, waveform_configs = full_pipeline.get_configs("test_default")

            assert waveform_configs["ms_before"] == waveform_configs["ms_after"]

            idx = indexes[0]

            for recording in recs_to_test:
                frame = (
                    waveform_configs["ms_before"]
                    / 1000
                    * recording.get_sampling_frequency()
                )

                data = recording.get_traces(
                    start_frame=idx - int(frame),
                    end_frame=idx + int(frame),
                    return_scaled=True,
                )
                data = data[:, waveforms.sparsity.unit_id_to_channel_indices[unit_idx]]

                assert np.array_equal(data, first_unit_waveforms[0])

    def write_an_empty_file_in_outputs(
        self, test_info, ses_name, run_name, sorter=DEFAULT_SORTER
    ):
        """
        Write a file called `test_file.txt` with contents `test_file` in
        the preprocessed, sorting and postprocessing output path for this
        session / run.
        """
        paths = self.get_output_paths(test_info, ses_name, run_name, sorter=sorter)

        paths_to_write = []
        for output in ["preprocessing", "sorting_path", "postprocessing"]:
            paths_to_write.append(paths[output] / "test_file.txt")

        for path_ in paths_to_write:
            with open(path_, "w") as file:
                file.write("test file.")

        return paths_to_write

    def get_output_paths(
        self,
        test_info,
        ses_name,
        run_name,
        sorter=DEFAULT_SORTER,
        concatenate_sessions=False,
        concatenate_runs=False,
    ):
        """
        Get the expected output paths for the `full_pipeline` output. These paths
        depend on whether session / run concatenation was performed.
        """
        base_path, sub_name, sessions_and_runs = test_info

        if concatenate_sessions:
            run_path = (
                base_path
                / "derivatives"
                / "spikewrap"
                / sub_name
                / f"{sub_name}-sorting-concat"
                / ses_name
                / "ephys"
            )
        elif concatenate_runs:
            run_path = (
                base_path
                / "derivatives"
                / "spikewrap"
                / sub_name
                / ses_name
                / "ephys"
                / f"{sub_name}-sorting-concat"
                / run_name
            )
        else:
            run_path = (
                base_path
                / "derivatives"
                / "spikewrap"
                / sub_name
                / ses_name
                / "ephys"
                / run_name
            )

        paths = {
            "preprocessing": run_path / "preprocessing",
            "sorting_path": run_path / sorter / "sorting",
            "postprocessing": run_path / sorter / "postprocessing",
        }
        paths["sorter_output"] = paths["sorting_path"] / "sorter_output"
        paths["recording_dat"] = paths["sorter_output"] / "recording.dat"

        return paths

    # ----------------------------------------------------------------------------------
    # Getters
    # ----------------------------------------------------------------------------------

    def get_test_rawdata_and_preprocessed_data(
        self, base_path, sub_name, ses_name, run_name
    ):
        """
        # Preprocess the rawdata, check it matches
        """
        rawdata_path = base_path / "rawdata" / sub_name / ses_name / "ephys" / run_name

        if DEFAULT_FORMAT == "spikeglx":
            test_rawdata = se.read_spikeglx(
                folder_path=rawdata_path.as_posix(), stream_id="imec0.ap"
            )
        elif DEFAULT_FORMAT == "spikeinterface":
            from spikeinterface import load_extractor

            test_rawdata = load_extractor(rawdata_path.as_posix())
        else:
            raise ValueError(f"Default normal {DEFAULT_FORMAT} is not recognised.")

        test_rawdata = astype(test_rawdata, np.float64)

        test_preprocessed = phase_shift(test_rawdata)
        test_preprocessed = bandpass_filter(
            test_preprocessed, freq_min=300, freq_max=6000
        )
        test_preprocessed = common_reference(
            test_preprocessed, operator="median", reference="global"
        )

        return test_rawdata, test_preprocessed

    def get_times_of_waveform_spikes(self, waveforms, sorting, unit_id):
        """
        Extract the peak times of the waveforms that were randomly sampled.
        SpikeInterface WaveformExtractor randomly samples a set of spikes
        from all spikes in a unit (default 500) to reduce computation time
        and memory footprint. As such, the index of the sampled waveforms
        is used in the list of all spike times to find the sampled spike times.

        TODO
        ----
        Check manually that the correct spike times are extracted, as compared with Phy.
        """
        select_waveform_tuples = waveforms.get_sampled_indices(unit_id)
        select_waveform_idxs, seg_idxs = zip(*select_waveform_tuples)
        assert np.all(np.array(seg_idxs) == 0), "Multi-segment waveforms not tested."

        all_waveform_peak_idxs = sorting.get_unit_spike_train(unit_id)
        selected_waveform_idxs = all_waveform_peak_idxs[np.array(select_waveform_idxs)]
        selected_waveform_peak_times = (
            selected_waveform_idxs / waveforms.sampling_frequency
        )

        return selected_waveform_peak_times, selected_waveform_idxs

    def get_pp_key(self, loaded_data_dict):
        return list(loaded_data_dict.keys())[-1]
