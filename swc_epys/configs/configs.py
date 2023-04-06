def get_configs(name):
    """
    TODO: must be a better way to handle path
    """
    with open(os.getcwd() / f"{name}.yaml"):
        pp_steps = yaml.full_load(config_file)
    return pp_steps