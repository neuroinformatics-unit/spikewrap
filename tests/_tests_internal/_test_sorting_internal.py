from __future__ import annotations

import shutil
from pathlib import Path

import pytest

import spikewrap as sw

DATA_SUB_PATH = r"/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/code/git-repos/SPIKEWRAP_TESTS/data/time-short/rawdata/1119617"
KILOSORT2_5_PATH = "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/code/git-repos/SPIKEWRAP_TESTS/matlab_repos/kilosort2_5/Kilosort"

KILOSORT2_5_PATH_NOMEX = "/ceph/neuroinformatics/neuroinformatics/scratch/jziminski/ephys/code/git-repos/SPIKEWRAP_TESTS/matlab_repos/kilosort2_5_nomex/Kilosort"

# TODO: expose a function like 'compile kilosort mex files..."
# TODO: test docker (on CI?)
# TODO: need to module load matlab for these tests
# TODO: need to expose "module load matlab" option in the slurm script.
# for now, just a way to add commands!
# and need to add a test here...
# TODO: check that tests are properly deleted, and check
# TODO: check sorter saved in the correct place!


class TestInternal:

    @pytest.fixture(scope="function")
    def prepro_session(self):
        """ """

        sub_path = Path(DATA_SUB_PATH)
        rawdata_path = sub_path.parent
        assert rawdata_path.name == "rawdata"
        derivatves_path = rawdata_path.parent / "derivatives"

        if derivatves_path.is_dir():
            shutil.rmtree(derivatves_path)

        session = sw.Session(
            subject_path=DATA_SUB_PATH,
            session_name="ses-001",
            file_format="spikeglx",
        )

        # TODO: document well the class lifespan
        session.preprocess(
            configs="neuropixels+kilosort2_5",  # prepo same for all sorters...
            per_shank=True,
            concat_runs=True,
        )
        return session

    def test_kilosort4_local(self, prepro_session):

        config_dict = {"kilosort4": {}}
        prepro_session.sort(config_dict, "local")

    def test_kilosort2_5_path(self, prepro_session):

        config_dict = {"kilosort2_5": {}}

        prepro_session.sort(
            config_dict,
            KILOSORT2_5_PATH,
            slurm=False,
        )

    def test_kilosort2_5_nomex(self, prepro_session):

        config_dict = {"kilosort2_5": {}}

        with pytest.raises(RuntimeError) as e:
            prepro_session.sort(
                config_dict,
                KILOSORT2_5_PATH_NOMEX,
            )
        assert "No mex files found" in str(e.value)

    def test_kilosort2_5_singularity(self, prepro_session):
        config_dict = {"kilosort2_5": {}}

        prepro_session.sort(
            config_dict,
            "singularity",
        )

        # TODO: check sorter saved in the correct place!
