import pytest
import numpy as np
import spikewrap as sw
from pathlib import Path
import spikeinterface.full as si
import pickle

def test_preprocessing_pickling():
    """Test that preprocessing objects are correctly pickled during SLURM execution."""
    # Get example data path
    example_data = sw.get_example_data_path("spikeglx") / "rawdata" / "sub-001"
    
    # Create two identical sessions
    session_local = sw.Session(
        subject_path=example_data,
        session_name="ses-001",
        file_format="spikeglx"
    )
    
    session_slurm = sw.Session(
        subject_path=example_data,
        session_name="ses-001",
        file_format="spikeglx"
    )

    # Use simple preprocessing steps for testing
    pp_steps = {
        "1": ["phase_shift", {}],
        "2": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
        "3": ["common_reference", {"operator": "median", "reference": "global"}],
    }

    # Process both sessions
    session_local.preprocess(configs=pp_steps, per_shank=False, concat_runs=False)
    session_slurm.preprocess(configs=pp_steps, per_shank=False, concat_runs=False)

    # Save with and without SLURM
    session_local.save_preprocessed(overwrite=True, n_jobs=1, slurm=False)
    session_slurm.save_preprocessed(overwrite=True, n_jobs=1, slurm=True)

    # Compare the results
    local_runs = session_local.get_preprocessed_run_names()
    slurm_runs = session_slurm.get_preprocessed_run_names()

    assert local_runs == slurm_runs, "Run names should match between local and SLURM execution"

    for run_name in local_runs:
        local_recording = session_local._pp_runs[run_name]._preprocessed
        slurm_recording = session_slurm._pp_runs[run_name]._preprocessed

        # Compare recording objects
        assert local_recording.keys() == slurm_recording.keys(), f"Recording keys don't match for run {run_name}"
        
        for key in local_recording.keys():
            local_data = local_recording[key]
            slurm_data = slurm_recording[key]

            # Compare key properties
            assert local_data.get_num_channels() == slurm_data.get_num_channels()
            assert local_data.get_num_segments() == slurm_data.get_num_segments()
            assert local_data.get_sampling_frequency() == slurm_data.get_sampling_frequency()

            # Compare actual data content
            local_traces = local_data.get_traces(start_frame=0, end_frame=1000)
            slurm_traces = slurm_data.get_traces(start_frame=0, end_frame=1000)
            np.testing.assert_array_almost_equal(local_traces, slurm_traces)

def test_direct_pickling():
    """Test direct pickling/unpickling of preprocessing objects."""
    example_data = sw.get_example_data_path("spikeglx") / "rawdata" / "sub-001"
    
    session = sw.Session(
        subject_path=example_data,
        session_name="ses-001",
        file_format="spikeglx"
    )

    pp_steps = {
        "1": ["phase_shift", {}],
        "2": ["bandpass_filter", {"freq_min": 300, "freq_max": 6000}],
    }

    session.preprocess(configs=pp_steps, per_shank=False, concat_runs=False)

    # Test pickling of preprocessed run objects
    for run_name, pp_run in session._pp_runs.items():
        # Pickle and unpickle
        pickled_data = pickle.dumps(pp_run)
        unpickled_run = pickle.loads(pickled_data)

        # Compare original and unpickled objects
        assert pp_run._raw_data_path == unpickled_run._raw_data_path
        assert pp_run._ses_name == unpickled_run._ses_name
        assert pp_run._run_name == unpickled_run._run_name
        assert pp_run._file_format == unpickled_run._file_format
        assert pp_run._pp_steps == unpickled_run._pp_steps

        # Compare recording objects
        orig_recording = pp_run._preprocessed
        unpickled_recording = unpickled_run._preprocessed

        assert orig_recording.keys() == unpickled_recording.keys()
        
        for key in orig_recording.keys():
            orig_data = orig_recording[key]
            unpickled_data = unpickled_recording[key]

            # Compare properties
            assert orig_data.get_num_channels() == unpickled_data.get_num_channels()
            assert orig_data.get_num_segments() == unpickled_data.get_num_segments()
            assert orig_data.get_sampling_frequency() == unpickled_data.get_sampling_frequency()

            # Compare actual data
            orig_traces = orig_data.get_traces(start_frame=0, end_frame=1000)
            unpickled_traces = unpickled_data.get_traces(start_frame=0, end_frame=1000)
            np.testing.assert_array_almost_equal(orig_traces, unpickled_traces)

if __name__ == "__main__":
    pytest.main([__file__]) 