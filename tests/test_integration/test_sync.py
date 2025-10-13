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
            assert (
                run_name == session._passed_run_names[run_idx]
            ), f"session.get_raw_run_names(){session.get_raw_run_names()} ------  session._passed_run_names {session._passed_run_names}"

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

        # Check that the sync data is silenced
        run_1_sync = session.get_sync_channel(0)
        run_2_sync = session.get_sync_channel(1)

        assert np.all(run_1_sync[:10] == 0)
        assert np.all(run_1_sync[10:] == 1)

        assert np.all(run_2_sync[0:50] == 1)
        assert np.all(run_2_sync[50:550] == 0)
        assert np.all(run_2_sync[550:800] == 1)
        assert np.all(run_2_sync[800:899] == 0)
        assert np.all(run_2_sync[899:] == 1)

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

    def test_save_sync(self, session):
        """
        Test sync channel saves correctly
        and the overwrite flag works as expected
        """

        # Load raw data, edit it, save and reload checking
        # reloaded data is correct
        session.load_raw_data()

        session.silence_sync_channel(1, [(250, 500)])

        session.save_sync_channel()

        load_1_sync = np.load(
            session._output_path / "recording1" / "sync" / "sync_channel.npy"
        )
        load_2_sync = np.load(
            session._output_path / "recording2" / "sync" / "sync_channel.npy"
        )

        assert np.all(load_1_sync == 1)
        assert np.all(load_2_sync[:250] == 1)
        assert np.all(load_2_sync[250:500] == 0)

        # Overwrite the sync data, then try and save
        # (should raise error with overwrite false)
        session.load_raw_data(overwrite=True)

        with pytest.raises(RuntimeError):
            session.save_sync_channel()  # overwrite False is expected default

        # Now save it and check the overwritten
        # sync data is saved
        session.save_sync_channel(overwrite=True)

        load_2_sync = np.load(
            session._output_path / "recording2" / "sync" / "sync_channel.npy"
        )
        assert np.all(load_2_sync == 1)
