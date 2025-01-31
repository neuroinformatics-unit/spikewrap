(how-to-install)=
# How to Install

The simplest way to install spikewrap is with `pip`, a package manager that is 
automatically included with Python.

:::{admonition} Using `pip`
:class: note

`pip` is run through the system terminal, and is best used in a virtual environment 
(such as `virtualenv` or `conda`). For more on getting set up with Python, see
[Virtual Environments, a Primer](https://realpython.com/python-virtual-environments-a-primer/)
:::

## Installation instructions

:::{warning}
``spikewrap`` is currently in the [alpha](https://en.wikipedia.org/wiki/Software_release_life_cycle#Alpha) release phase. 
Please  get in contact if you experience any bugs or unexpected behaviour.
:::

::::{tab-set}

:::{tab-item} Pip

``spikewrap`` can be installed with the `pip` command:

```sh
pip install spikewrap
```

This will install spikewrap and all dependencies, including 
[SpikeInterface](https://spikeinterface.readthedocs.io/en/stable/).

``spikewrap`` will be linked to a specific 
[SpikeInterface](https://spikeinterface.readthedocs.io/en/stable/)
version, so it is not recommended to install 
[SpikeInterface](https://spikeinterface.readthedocs.io/en/stable/)
separately.

:::

:::{tab-item} Developers

`pip` can also be used to install developer dependencies.

Clone the spikewrap
[GitHub repository](https://github.com/neuroinformatics-unit/spikewrap/)
to get the latest development version.

To install spikewrap and its developer dependencies,
run the follow command from inside the repository:

```sh
pip install -e .[dev]  # works on most shells
pip install -e '.[dev]'  # works on zsh (the default shell on macOS)
```

This will install an 'editable' version of spikewrap, meaning
any changes you make to the cloned code will be immediately
reflected in the installed package.

TODO: link the contributing guide
:::

::::

## Check the installation

Check the ``spikewrap`` version with:

```sh
pip spikewrap --version
```

and the 
[SpikeInterface](https://spikeinterface.readthedocs.io/en/stable/)
version that was installed:

```sh
pip spikeinterface --version
```
