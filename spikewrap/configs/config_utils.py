import glob
import itertools
import os
import shutil
from pathlib import Path

import yaml

from spikewrap.process import _preprocessing
from spikewrap.utils import _utils


def get_configs(name: str) -> tuple[dict, dict]:
    """
    Loads a config yaml file from the default config path.

    Parameters
    ----------
    name: name of the configs to load.
          Should not include the .yaml suffix.

    Returns
    -------

    pp_steps
        a dictionary containing the preprocessing
       step order (keys) and a [pp_name, kwargs]
       list containing the spikeinterface preprocessing
       step and keyword options.

    sorter_options
        a dictionary with sorter name (key) and
        a dictionary of kwargs to pass to the
        spikeinterface sorter class.
    """
    config_dir = get_configs_path()

    available_files = glob.glob((config_dir / "*.yaml").as_posix())
    available_files = [Path(path_).stem for path_ in available_files]

    if name not in available_files:
        # then assume it is a full path

        assert Path(name).is_file(), (
            f"{name} is neither the name of an existing "
            f"config or valid path to configuration file."
        )

        assert Path(name).suffix in [
            ".yaml",
            ".yml",
        ], f"{name} is not the path to a .yaml file"

        config_filepath = Path(name)

    else:
        config_filepath = config_dir / f"{name}.yaml"

    with open(config_filepath) as file:
        config = yaml.full_load(file)

    pp_steps = config.get("preprocessing", {})
    sorting = config.get("sorting", {})

    return pp_steps, sorting


def get_configs_path() -> Path:
    """
    Get the path to the User home directory folder
    in which all spikewrap config yamls are stored.

    Returns
    -------
    Path
        The path to the spikewrap `configs` directory.
    """
    configs_path = Path.home() / ".spikewrap" / "configs"

    if not configs_path.is_dir():
        _create_user_configs_folder(configs_path)

    return configs_path


def _create_user_configs_folder(configs_path: Path) -> None:
    """
    Create the spikewrap configs path where config YAML files
    are stored. Copy the YAMLs  from the spikewrap install
    directory (we do not want to manage files directly in the
    installation directory, due to potential permissions issues).

    Once this folder is set up, all config YAMLs are managed
    in the user directory.
    """
    configs_path.mkdir(parents=True)

    default_configs_path = (
        Path(os.path.dirname(os.path.realpath(__file__)))
        / "_backend"
        / "_default_configs"
    )
    for config_filepath in list(
        default_configs_path.glob("*.yaml")
    ):  # TODO: store canon suffix
        shutil.copy(config_filepath, configs_path)


def show_available_configs() -> None:
    """
    Print the file names of all YAML config
    files in the user config path.
    """
    configs_path = get_configs_path()

    yaml_paths = itertools.chain(
        configs_path.glob("*.yaml"), configs_path.glob("*.yml")
    )

    yaml_names = [path_.name for path_ in yaml_paths]

    _utils.message_user(f"The available configs are:\n" f"{yaml_names}")


def save_config_dict(config_dict: dict, name: str, folder: Path | None = None):
    """
    Save a configuration dictionary to a YAML file.

    Parameters
    ----------
    config_dict
        The configs dictionary to save.
    name
        The name of the YAML file (with or without the `.yaml` extension).
    folder
        If None (default), the config is saved in the spikewrap-managed
        user configs folder. Otherwise, save in `folder`.
    """
    if folder is None:
        folder = get_configs_path()

    output_filepath = Path(folder) / name

    if not output_filepath.suffix:
        output_filepath = output_filepath.with_suffix(".yaml")  # use canonical

    _utils._dump_dict_to_yaml(output_filepath, config_dict)


def load_config_dict(filepath: Path) -> dict:
    """
    Load a configuration dictionary from a YAML file.

    Parameters
    ----------
    filepath
        The full path to the YAML file, including the file name and extension.

    Returns
    -------
    dict
        The configs dict loaded from the YAML file.
    """
    if not filepath.is_file():
        raise FileNotFoundError(f"No file found at {filepath}.")

    if filepath.suffix not in [".yml", ".yaml"]:  # TODO: centralise
        raise ValueError(
            f"File {filepath.name} is not a yaml file, must end in .yml or .yaml"
        )

    return _utils._load_dict_from_yaml(filepath)


def show_configs(name: str) -> None:
    """
    Print the configuration options.
    """
    pp_steps, sorting = get_configs(name)

    _utils.show_preprocessing_configs(pp_steps)
    _utils.show_sorting_configs(sorting)


def show_supported_preprocessing_steps() -> None:
    """
    Print the (currently supported) SpikeInterface
    preprocessing steps.
    """
    pp_steps = _preprocessing._get_pp_funcs()

    _utils.message_user(
        f"Currently supported preprocessing steps are:\n" f"{list(pp_steps.keys())}"
    )
