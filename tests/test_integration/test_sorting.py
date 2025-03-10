from __future__ import annotations

import shutil
import sys

import pytest
from base import BaseTest

import spikewrap as sw


class TestSorting(BaseTest):

    def get_prepro_sesion(self, prepro_per_shank, prepro_concat_runs):
        """
        Generate a quick, preprocessed session object
        """
        mock_probe = self.get_mock_probe()

        sub_path = self.get_no_probe_sub_path()

        rawdata_path = sub_path.parent
        assert rawdata_path.name == "rawdata"

        derivatives_path = sub_path.parent.parent / "derivatives"
        if derivatives_path.is_dir():
            shutil.rmtree(derivatives_path)

        session = sw.Session(
            sub_path,
            "ses-001",
            "openephys",
            "all",
            probe=mock_probe,
        )

        session.preprocess(
            self.get_pp_steps(),
            per_shank=prepro_per_shank,
            concat_runs=prepro_concat_runs,
        )

        session.save_preprocessed()

        return session

    def get_configs(self):
        config_dict = sw.load_config_dict(
            sw.get_configs_path() / "neuropixels+mountainsort5.yaml"
        )
        config_dict["sorting"]["mountainsort5"] = {"whiten": False}
        return config_dict

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    def test_bad_per_shank(self):
        """
        Cannot sort per-shank if preprocessing was run per shank.
        """
        prepro_per_shank = True
        prepro_concat_runs = False

        sort_per_shank = True
        sort_concat_runs = False

        session = self.get_prepro_sesion(prepro_per_shank, prepro_concat_runs)

        with pytest.raises(ValueError):
            session.sort(
                self.get_configs(),
                run_sorter_method="local",
                per_shank=sort_per_shank,
                concat_runs=sort_concat_runs,
                overwrite=True,
            )

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    def test_bad_concat_run(self):
        """
        Cannot concatenate runs for sorting if raw data
        was already concatenated for preprocessing.
        """
        prepro_per_shank = False
        prepro_concat_runs = True

        sort_per_shank = False
        sort_concat_runs = True

        session = self.get_prepro_sesion(prepro_per_shank, prepro_concat_runs)

        with pytest.raises(ValueError):
            session.sort(
                self.get_configs(),
                run_sorter_method="local",
                per_shank=sort_per_shank,
                concat_runs=sort_concat_runs,
                overwrite=True,
            )

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    def test_prepro_per_shank(self):
        """
        Check outputs when runs are split-per-shank for preprocessing
        and then the split recording is sorted.
        """
        prepro_per_shank = True
        prepro_concat_runs = False

        sort_per_shank = False
        sort_concat_runs = False

        session = self.get_prepro_sesion(prepro_per_shank, prepro_concat_runs)

        session.sort(
            self.get_configs(),
            run_sorter_method="local",
            per_shank=sort_per_shank,
            concat_runs=sort_concat_runs,
            overwrite=True,
        )

        for run_name in session.get_preprocessed_run_names():

            out_path = session._output_path / run_name

            assert (out_path / "preprocessed" / "shank_0").is_dir()
            assert (out_path / "sorting" / "shank_0").is_dir()

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    def test_prepro_concat_run(self):
        """
        Check outputs when runs are concatenated for preprocessing
        and then the split recording is sorted.
        """
        prepro_per_shank = False
        prepro_concat_runs = True

        sort_per_shank = False
        sort_concat_runs = False

        session = self.get_prepro_sesion(prepro_per_shank, prepro_concat_runs)

        session.sort(
            self.get_configs(),
            run_sorter_method="local",
            per_shank=sort_per_shank,
            concat_runs=sort_concat_runs,
            overwrite=True,
        )

        out_path = session._output_path / "concat_run"

        assert (out_path / "preprocessed" / "properties").is_dir()
        assert (out_path / "sorting" / "sorter_output").is_dir()

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    def test_prepro_per_shank_and_concat_runs(self):
        """
        Check outputs when runs are both split-by-shank and
        concatenated for preprocessing and then the split recording is sorted.
        """
        prepro_per_shank = True
        prepro_concat_runs = True

        sort_per_shank = False
        sort_concat_runs = False

        session = self.get_prepro_sesion(prepro_per_shank, prepro_concat_runs)

        session.sort(
            self.get_configs(),
            run_sorter_method="local",
            per_shank=sort_per_shank,
            concat_runs=sort_concat_runs,
            overwrite=True,
        )

        out_path = session._output_path / "concat_run"

        assert (out_path / "preprocessed" / "shank_0").is_dir()
        assert (out_path / "sorting" / "shank_0").is_dir()

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    def test_sort_per_shank(self):
        """
        Test when runs are split-by-shank after preprocessing, before sorting
        """
        prepro_per_shank = False
        prepro_concat_runs = False

        sort_per_shank = True
        sort_concat_runs = False

        session = self.get_prepro_sesion(prepro_per_shank, prepro_concat_runs)

        session.sort(
            self.get_configs(),
            run_sorter_method="local",
            per_shank=sort_per_shank,
            concat_runs=sort_concat_runs,
            overwrite=True,
        )

        for run_name in session.get_preprocessed_run_names():
            assert (
                session._output_path / run_name / "preprocessed" / "properties"
            ).is_dir()
            assert (session._output_path / run_name / "sorting" / "shank_0").is_dir()

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    def test_sort_concat_runs(self):
        """
        Test when runs are  concatenated after
        preprocessing, before sorting
        """
        prepro_per_shank = False
        prepro_concat_runs = False

        sort_per_shank = False
        sort_concat_runs = True

        session = self.get_prepro_sesion(prepro_per_shank, prepro_concat_runs)

        session.sort(
            self.get_configs(),
            run_sorter_method="local",
            per_shank=sort_per_shank,
            concat_runs=sort_concat_runs,
            overwrite=True,
        )

        for run_name in session.get_preprocessed_run_names():
            assert (
                session._output_path / run_name / "preprocessed" / "properties"
            ).is_dir()

        assert (
            session._output_path / "concat_run" / "sorting" / "sorter_output"
        ).is_dir()

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    def test_sort_per_shank_and_concat_runs(self):
        """
        Test when runs are split-per-shank and
        concatenated after preprocessing.
        """
        prepro_per_shank = False
        prepro_concat_runs = False

        sort_per_shank = True
        sort_concat_runs = True

        session = self.get_prepro_sesion(prepro_per_shank, prepro_concat_runs)

        session.sort(
            self.get_configs(),
            run_sorter_method="local",
            per_shank=sort_per_shank,
            concat_runs=sort_concat_runs,
            overwrite=True,
        )

        for run_name in session.get_preprocessed_run_names():
            assert (
                session._output_path / run_name / "preprocessed" / "properties"
            ).is_dir()

        assert (
            session._output_path
            / "concat_run"
            / "sorting"
            / "shank_0"
            / "sorter_output"
        ).is_dir()

    @pytest.mark.skipif(
        sys.platform == "darwin", reason="Isoplit not installing on macOS"
    )
    @pytest.mark.parametrize("prepro_per_shank", [True, False])
    def test_load_prepro_from_file_for_sorting(self, prepro_per_shank):
        """
        Test when session is created without preprocessing, the preprocessed
        data should be loaded from file for sorting.
        """
        session = self.get_prepro_sesion(prepro_per_shank, False)

        session = sw.Session(
            session._parent_input_path,
            session._ses_name,
            session._file_format,
            session._passed_run_names,
            probe=session._probe,
        )
        assert session.get_preprocessed_run_names() == []

        session.sort(
            self.get_configs(),
            run_sorter_method="local",
            per_shank=False,
            concat_runs=False,
            overwrite=True,
        )
