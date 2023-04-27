from .data_class import Data
import spikeinterface.extractors as se
from spikeinterface import append_recordings

def load_spikeglx_data(base_path, sub_name, run_name):  # TODO: currently only spikeglx supported
    """
    """
    data = Data(base_path, sub_name, run_name)

    data.run_level_path = data.rawdata_path / sub_name / f"{run_name}_g0"  # TODO: fix this higher up...? HANDLE IT IN DATA!!!  '"RUN LEVLE PATHS'

    if run_name == ["all"] or len(run_name) > 1:  # TOOD: rename as run_name
        all_run_names = (base_path / "rawdata" / sub_name).glob(f"*_g0")  # TODO: this is a dumb way to search?

        searched_run_names = [path_.stem for path_ in all_run_names]

        if run_name != ["all"]:  # TODO: test this case
            check_run_names = [f"{run_name}_g0" for name in run_name]
            searched_run_names = [name for name in searched_run_names if name in check_run_names]

        run_name = searched_run_names

        all_recordings = [se.read_spikeglx(folder_path=(base_path / "rawdata" / sub_name / f"{name}"), stream_id="imec0.ap", all_annotations=True) for name in run_name]

        # need to do some validation before this concat incase the assumptions of the SI segment are broken
        data["0-raw"] = append_recordings(all_recordings)

    else:
        data["0-raw"] = se.read_spikeglx(folder_path=data.run_level_path,
                                         stream_id="imec0.ap", all_annotations=True)

    return data

