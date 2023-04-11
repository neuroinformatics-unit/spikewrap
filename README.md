> [!warning] SWC Ephys is not sufficiently tested to be used in analysis. This release is only for testing. Do not use for your final analyses.

> [!warning] Limitations
> - works only on SpikeGLX recordings with 1 gate, trigger, probe (per run)
> - requires standard input folder format
> - has limited preprocessing options (`tshift`, `bandpass_filter`, `common median reference`)
> - no options to remove potentially large intermediate files
> - untested!


# Installation

Clone [the repository]() using git. Change directory to the repo and install using

`pip install -e .`

or, to also install developer dependencies

`pip install -e .[dev]` (Windows) 
or 
`pip install -e '.[dev]'` (macOS / Linux)

After installation, the module can be imported with `import swc_ephys`. Local installations can be used to visualise preprocessing results (see below). To run sorting, running on the SWC HPC is currently required.

#### Running on the HPC

Currently, sorting is required to run on the SWC HPC with access to `/ceph/neuroinformatics`. This allows KiloSort to be run, which have NVIDIA GPU as a requirement. 

To connect and run on the HPC (e.g. from Windows, macOS or Linux terminal):

`ssh username@ssh.swc.ucl.ac.uk` 
`ssh hpc-gw`1

The first time using, it is necessary to steup and install `swc_ephys`. It is strongly recommended to make a new conda environment on the HPC, before installing `swc_ephys` as above. 

`module load miniconda`
`conda create --name swc_ephys python=3.10`
`conda activate swc_ephys`

and install swc_ephys and it's dependencies

`mkdir ~/git-repos`
`cd ~/git-repos`
`git clone https://github.com/JoeZiminski/swc_ephys.git`
`cd swc_ephys`
`pip install -e .`

Finally, to run the pipeline, create a script to run the pipeline or call from the command line interface (see below) and call it from the HPC, after requesting a GPU node

`srun -p gpu --gres=gpu:2 --mem=50000 --pty bash -i`
`module load miniconda`
`conda activate swc_ephys`
`python my_pipeline_script.py`

## Quick Start Guide

SWC Ephys (currently) expects input raw data to be stored in a `rawdata` folder. A subject (e.g. mouse) data should be stored in the `rawdata` folder and contain SpikeGLX format output (example below).**Currently, only recordings with 1 gate, 1 trigger and 1 probe (i.e. index 0 for all gate, trigger probe, `g0`, `t0` and `imec0`)**.

```
└── rawdata/
    └── 1110925/
        └── 1110925_test_shank1_g0/
            └── 1110925_test_shank1_g0_imec0/
                ├── 1110925_test_shank1_g0_t0.imec0.ap.bin
                └── 1110925_test_shank1_g0_t0.imec0.ap.meta
```


#### API (script) 

An example script to analyse this data is below

```
from swc_ephys.pipeline.full_pipeline import run_full_pipeline  
  
base_path = "/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning"  

if __name__ == "__main__":  

    run_full_pipeline(  
        base_path=base_path,  
        sub_name="1110925",  
        run_name="1110925_test_shank1",  
        config_name="test",  
        sorter="kilosort2_5",  
    )
```

Note `run_full_pipline` must be run in the `if __name__ == "__main__"` block as above as it requires `multiprocessing`.

The `base_path` is the path containing the required `rawdata` folder. `sub_name` is the subject to run, and `run_name` is the SpikeGLX run name to run. `configs_name` contains the name of the preprocessing / sorting settings to use (see below), and `sorter` is the name of the sorter to use (currently supported is `kilosort2`, `kilosort2_5` and `kilosort3`)

#### Command Line Interface

Alternatively, `swc_ephys` can be run using the command line with required poisitional arguments `base_path`, `sub_name` and `run_name` and optional arguments `--config_name` (default `test`), `--sorter` (default `kilosort2_5`) and flag `--use-existing-preprocessed-file`. For example, to run the script above using the command line

```
swc_ephys \
/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning \
1110925 \
1110925_test_shank1 \
--config-name test \
--sorter kilosort2_5
```

#### Output

Output of spike sorting will be in a `derivatives` folder at the same level as the `rawdata` where subfolder organisation matches that of `rawdata`. Output are the saved preprocessed data, spike sorting results as well as a list of [quality check measures](https://spikeinterface.readthedocs.io/en/latest/modules/qualitymetrics.html). For example, the full output of a sorting run with the input data as above is:

```
├── rawdata/
│   └── ...
└── derivatives/
    └── 1110925/
        └── 1110925_test_shank1_g0  /
            └── 1110925_test_shank1_g0_imec0/
                ├── preprocessed/
                │   ├── data_class.pkl
                │   └── si_recording
                ├── kilosort2_5-sorting/
                    ├── in_container_sorting/
                    ├── sorter_output/
                    ├── waveforms/
                    │   └── <spikeinterface waveforms output>
                    ├── quality_metrics.csv
                    ├── spikeinterface_log.json
                    ├── spikeinterface_params.json
                    └── spikeinterface_recording.json
```


**preprocessed**: contains the spikeinterface recording from the last preprocessing step saved in binary format (`si_recording`) and a `data_class.pkl`  used for internal swc_ephys use.

**-sorting output (e.g. kilosort2_5-sorting**: Multiple sorters may be run, and the output of different sorters saved here. A sorter output contains:
		- <u>in_container_sorting</u>:  stored options used to run the sorter
		- <u>sorter_output</u>: the full output of the sorter (e.g. kilosort .npy files)
		- <u>waveforms</u>: spikeinterface [waveforms](https://spikeinterface.readthedocs.io/en/latest/modules/core.html#waveformextractor) output containing AP waveforms for detected spikes
		- quality_metrics.csv: output of spikeinterface  [quality check measures](https://spikeinterface.readthedocs.io/en/latest/modules/qualitymetrics.html)
		- spikeinterface*.json: 


### Set Preprocessing Options

Preprocessing options available in SpikeInterface may be run. Currently supported are multiplexing correction or tshift (termed  `phase shift` here), common median referencing (CMR) (termed `common_reference` here) and bandpass filtering (`bandpass_filter`).

Preprocessing options are set in `yaml` configuration files stored in `sbi_ephys/sbi_ephys/configs/`.  A default pipeline is stored in `test.yaml`.

Custom preprocessing configuration files may be passed to the `config_name` argument, by passing the full path to the `.yaml` configuration file **TODO**. Configuration files are structured as a dictinoary with keys indicating the order ro run preprocessing, and values containing a list in which the first element in the name of the preprocessing to run, and the second element a dictionary containing options.

### Visualise Preprocessing

Visualsing preprocesing output can be run locally to inspect efficiacy of preprocessing rountines. To visualise preprocessing outputs:

```
from swc_ephys.pipeline.preprocess import preprocess  
from swc_ephys.pipeline.visualise import visualise  
  
base_path = "/ceph/neuroinformatics/neuroinformatics/scratch/ece_ephys_learning"  
sub_name = "1110925"  
run_name = "1110925_test_shank1"  
  
data = preprocess(base_path=base_path, sub_name=sub_name, run_name=run_name)  
  
visualise(  
    data,  
    steps="all",  
    mode="map",  
    as_subplot=True,  
    channel_idx_to_show=np.arange(10, 50),  
    show_channel_ids=False,  
    time_range=(1, 2),  
)
```

This will display a plot showing data from all preprocessing steps,  displaying channels with idx 10 - 50, over time period 1-2. Note this requires a GUI (i.e. not run on the HPC terminal) and is best run locally.

![[Pasted image 20230412145101.png]]

