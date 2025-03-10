from __future__ import annotations

import numpy as np
import pytest
from base import BaseTest

import spikewrap as sw


class TestSorting(BaseTest):

    @pytest.fixture(scope="function")
    def session(self, tmp_path):

        session = sw.Session(
            subject_path=sw.get_example_data_path("openephys") / "rawdata" / "sub-001",
            session_name="ses-001",
            file_format="openephys",
            run_names=["recording1", "recording2"],
            output_path=tmp_path,
        )

        # no need to tear down as each run is in a new `tmp_path`
        return session

    def test_run_name_matches_index(self, session):
        """
        Check the runs are stored in the correct order
        everywhere they are stored in the session object.
        """
        session.load_raw_data()

        for run_idx, run_name in enumerate(session.get_raw_run_names()):
            assert session._raw_runs[run_idx]._run_name == run_name
            assert run_name == session._passed_run_names[run_idx]

    def test_get_sync(self, session):
        """
        Check that getting the sync channel works for all runs
        """
        session.load_raw_data()

        num_samples = session._raw_runs[0]._raw["grouped"].get_num_samples()

        for run_idx, _ in enumerate(session.get_raw_run_names()):
            # no idea why np.array_equal is failing, np.unique both arrays is [1] dtype int16
            assert np.allclose(
                session.get_sync_channel(run_idx), np.ones(num_samples, dtype=np.int16)
            )

    def test_silence_then_concat_sync(self, session):

        session.load_raw_data()

        # Silence raw runs at some specific points, and define
        # some checkers to ensure the data is correct. Relies on the fact
        # the example data sync channel is all ones.
        session.silence_sync_channel(run_idx=0, periods_to_silence=[(0, 10)])
        session.silence_sync_channel(
            run_idx=1, periods_to_silence=[(50, 550), (800, 899)]
        )

        def check_run_1(sync_1):
            assert np.all(sync_1[:10] == 0)
            assert np.all(sync_1[10:] == 1)

        def check_run_2(sync_2):
            assert np.all(sync_2[0:50] == 1)
            assert np.all(sync_2[50:550] == 0)
            assert np.all(sync_2[550:800] == 1)
            assert np.all(sync_2[800:899] == 0)
            assert np.all(sync_2[899:] == 1)

        # Check that the sync data is silenced
        run_1_sync = session.get_sync_channel(0)
        run_2_sync = session.get_sync_channel(1)

        check_run_1(run_1_sync)
        check_run_2(run_2_sync)

        # and that these changes are propagated to the preprocessing
        session.preprocess("neuropixels+mountainsort5", concat_runs=False)

        check_run_1(session._pp_runs[0]._sync_data)
        check_run_2(session._pp_runs[1]._sync_data)

        # and that these changes are propagated and in the correct order
        # when preprocessed data is concatenated.
        session.preprocess("neuropixels+mountainsort5", concat_runs=True)
        concat_sync = session._pp_runs[0]._sync_data

        run_1_from_concat = concat_sync[:1000]
        run_2_from_concat = concat_sync[1000:]

        check_run_1(run_1_from_concat)
        check_run_2(run_2_from_concat)

        # and that the concat data is saved correctly
        session.save_preprocessed()

        load_sync = np.load(
            session._output_path / "concat_run" / "sync" / "sync_channel.npy"
        )

        check_run_1(load_sync[:1000])
        check_run_2(load_sync[1000:])

    def test_plot_sync(self, session):
        """
        Silence the first run, then check that the changes
        are properly propagated to the plotting. Assumes
        test data is example data with 1000 samples, sync channel all ones.
        """
        session.load_raw_data()

        session.silence_sync_channel(0, [(0, 500)])

        plot_1 = session.plot_sync_channel(run_idx=0, show=False)[0]
        assert np.array_equal(plot_1.get_xdata(), np.arange(1000))
        assert np.array_equal(plot_1.get_ydata(), np.r_[np.zeros(500), np.ones(500)])

        plot_2 = session.plot_sync_channel(run_idx=1, show=False)[0]
        assert np.array_equal(plot_2.get_xdata(), np.arange(1000))
        assert np.array_equal(plot_2.get_ydata(), np.ones(1000))

    def test_multi_load_raw_data(self, session):
        """
        Test sync data is properly refreshed when loading from file
        """
        assert not any(session._raw_runs)

        # Cannot work with sync channels until data loaded
        with pytest.raises(RuntimeError):
            session.get_sync_channel(0)

        with pytest.raises(RuntimeError):
            session.silence_sync_channel(0, [(0, 10)])

        # Load and edit some sync data
        session.load_raw_data()

        session.silence_sync_channel(0, [(0, 1000)])

        assert np.allclose(session.get_sync_channel(0), np.zeros(1000, dtype=np.int16))

        # Must use overwrite if re-loading
        with pytest.raises(RuntimeError):
            session.load_raw_data()

        # Check that reloading raw data has overwritten sync channel
        session.load_raw_data(overwrite=True)

        assert np.allclose(session.get_sync_channel(0), np.ones(1000))

    def test_edit_sync_after_preprocessing(self, session):
        """
        For now, to keep workflows less confusing, do not allow
        working with the sync channel after preprocessing is performed.

        This is because it is confusing to work with sync channel
        after preprocessing - what sync channel do we get? preprocessed
        or raw?
        """
        session.preprocess("neuropixels+mountainsort5")

        with pytest.raises(RuntimeError):
            session.get_sync_channel(0)

        with pytest.raises(RuntimeError):
            session.silence_sync_channel(0, [(0, 10)])

        with pytest.raises(RuntimeError):
            session.plot_sync_channel(0)
