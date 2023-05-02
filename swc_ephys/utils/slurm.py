from dask_jobqueue import SLURMCluster
from distributed import Client

def get_slurm_client():
    """
    account="woodshole",
    """
    cluster = SLURMCluster(cores=8,
                           processes=1,  # no idea what this actually means
                           memory="40GB",
                           walltime="01:00:00",
                           queue="normal",
                           worker_extra_args=["GPU=1"])
    client = Client(cluster)
    return client

def run_full_pipeline(**kwargs):
    breakpoint()
    client = get_slurm_client()
    client.submit(run_full_pipeline, **kwargs)