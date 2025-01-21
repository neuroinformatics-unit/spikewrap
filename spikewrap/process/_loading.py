import setuptools.config.pyprojecttoml
import spikeinterface.full as si
from spikewrap.utils import _utils


def load_data(run_path, file_format):
    """
    explain (e.g. without sync needed for sorting, otherwise store sync for
    storing the sync array!
    """
    filenames = [path_.name for path_ in run_path.rglob("*.*")]

    if file_format == "spikeglx":

        without_sync, with_sync = [
            si.read_spikeglx(
                folder_path=run_path,
                stream_id="imec0.ap",
                all_annotations=True,
                load_sync_channel=sync,
            )
            for sync in [False, True]
        ]


    elif file_format == "open_ephys":

        without_sync = si.read_openephys(
                folder_path=run_path,
                all_annotations=True,
                load_sync_channel=False,
        )
        try:
            with_sync = extractor(
                folder_path=run_path,
                all_annotations=False,
                load_sync_channel=True,
            )
        except ValueError:
            with_sync = None

    else:
        raise ValueError("Raw data type not recognised. Please contact spikewrap team.")

    if without_sync.get_num_segments() > 1:
        raise RuntimeError(f"Data at\n{run_path}\nhas multiple segments. "
                           f"This should nto be the case. "
                           f"Each run must contain only 1 recording.")

    return without_sync, with_sync

# -----------------------------------------------------------------------------
# Helpers
# -----------------------------------------------------------------------------

def is_spikeglx(filenames):
    """
    """
    has_meta = any(["ap.meta" in name for name in filenames])
    has_bin = any(["ap.bin" in name for name in filenames])

    return (has_meta and has_bin)


def is_openephys(filenames):
    """
    """
    has_oebin = any(["structure.oebin" == name for name in filenames])

    return has_oebin


def get_run_paths(file_format, ses_path, passed_run_names):
    # TEST THIS!
    # DOC THIS!

    if file_format == "spikeglx":

        detected_run_paths = [path_ for path_ in ses_path.glob("*g*_imec*") if path_.is_dir()]

        if not any (detected_run_paths):
            raise FileNotFoundError(f"No spikeglx run folders found at {ses_path}.")

        for path_ in detected_run_paths:
            rec_paths = list(path_.glob("*.bin"))
            if len(rec_paths) > 1:
                raise RuntimeError(f"The run folder {path_} contains more than one recording."
                                   f"Currently multi-trigger recordings are not supported."
                                   f"Plese contact the spikerwap team.")

            if len(rec_paths) == 0:
                raise RuntimeError(f"No recording found in run path: {path_}")

    elif file_format == "openephys":

        node_path = list(ses_path.glob("*Node*"))

        if len(node_path) > 1:
            raise RuntimeError(f"Only single-Node openephys recordings currently supported."
                               f"Multiple found at {ses_path}",
                               f"Please contact the spikewrap team.")

        if len(node_path) == 0:
            raise RuntimeError(f"No 'Node' openephys recordings found at {ses_path}.")

        experiment_path = list(node_path[0].glob("*experiment*"))

        if len(experiment_path) > 1:
            raise RuntimeError(f"Only single-'experiment' openephys recordings currently supported."
                               f"Multiple found at {node_path}"
                               f"Please contact the spikewrap team.")

        if len(experiment_path) == 0:
            raise RuntimeError(f"No 'experiment' openephys recordings found at {node_path}.")

        detected_run_paths = [path_ for path_ in experiment_path[0].glob("*recording*") if path_.is_dir()]

        # TODO: similar to the above loop
        for path_ in detected_run_paths:
            rec_paths = list(path_.glob("*continuous*"))
            if len(rec_paths) == 0:
                raise RuntimeError(f"No 'continuous' recording found in run path: {path_}")

    else:
        raise ValueError("`file_format` not recognised.")

    if passed_run_names == "all":
        run_paths = detected_run_paths
    else:
        detected_run_names = [path_.name for path_ in detected_run_paths]

        for passed_name in passed_run_names:
            if not passed_name in detected_run_names:
                raise ValueError(f"{passed_run_name} not found in folder: {ses_path}")

        run_paths = [path_ for path_ in detected_run_paths if path_.name in run_names]

    if not _utils.paths_are_in_datetime_order(run_paths, "creation"):
        warnings.warn(
            f"The sessions or runs provided for are not in creation datetime "
            f"order. \nThey will be concatenated in the order provided, as: "
            f"{[path_.name for path_ in run_paths]}."
        )

    return run_paths