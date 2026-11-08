# Kedro

Runs a pipeline of a Kedro project on the block's inputs and outputs the datasets it produces.

[Kedro](https://kedro.org/) is an open-source Python framework for data pipelines: a project declares its datasets in a catalog (`conf/base/catalog.yml`) and its steps as nodes of a pipeline. This block runs such a project from an Omniscope workflow:

- Each connected **input** is saved to the catalog dataset you name for it (for example the dataset `orders`, stored at `data/01_raw/orders.csv`), replacing what was there.
- The **pipeline** runs with Kedro's session API: the default pipeline, or one you name, in an optional configuration **environment**.
- Each **output** you name is read back after the run: a free output of the pipeline (a dataset not in the catalog), a catalog dataset, or `data/08_reporting/<name>.csv`.

A name the catalog doesn't declare is written to `data/01_raw/<name>.csv` and read from `data/08_reporting/<name>.csv`, as earlier versions of this block did.

## Language and libraries

Python. It uses [Kedro](https://github.com/kedro-org/kedro) (Apache License 2.0), version 0.19 or later, and pandas.

The manifest asks Omniscope to install `kedro>=0.19`. Everything the Kedro project itself uses must also be installed in Omniscope's Python environment: usually `kedro-datasets` (Apache License 2.0) with the extras for its dataset types, such as `kedro-datasets[pandas-csvdataset]`, and the project's own requirements.

## Inputs

- **Inputs 1 to 3**: the tables to feed the pipeline, each saved to the dataset named in its option. Connect only the ones you name.

## Options

| Option | Name in script | Type | Description |
|---|---|---|---|
| Kedro project folder | `path` | File | The Kedro project's top folder on the Omniscope server: the folder holding `pyproject.toml`. |
| Input dataset 1 | `input0` | Text | The catalog dataset that input 1 is saved to before the run, such as `orders`. |
| Input dataset 2 | `input1` | Text | The catalog dataset that input 2 is saved to. Empty when input 2 is not connected. |
| Input dataset 3 | `input2` | Text | The catalog dataset that input 3 is saved to. Empty when input 3 is not connected. |
| Output dataset 1 | `output0` | Text | The dataset to output as Dataset 1 after the run. Required. |
| Output dataset 2 | `output1` | Text | Optional second dataset to output, as Dataset 2. |
| Pipeline | `pipeline` | Text | A pipeline registered in the project's `pipeline_registry.py`. Empty for the default pipeline. |
| Environment | `env` | Text | A Kedro configuration environment (a folder in `conf/`, such as `prod`). Empty for Kedro's default. |

## Outputs

- **Dataset 1** (`Output Data`): the dataset named in Output dataset 1.
- **Dataset 2** (`Output Data 2`): the dataset named in Output dataset 2, if any.

## Limits

- The project must be on the Omniscope server's file system, and use Kedro 0.19 or later (projects from before 0.17, which had a `kedro_cli.py`, are not supported).
- The pipeline's nodes are Python code, run on the server with the permissions of Omniscope's Python process: point the block only at a project you trust.
- The inputs are written to the project's files: running the block changes the input datasets' files in the project folder, as running the pipeline yourself would. Input datasets must be stored datasets (files, databases), not memory datasets.
- Only tables can be output (a pandas DataFrame, or a Series as a one-field table). Models, dictionaries and other objects can't.
- The block passes the inputs to Kedro with the types Omniscope gives them (whole numbers as nullable integers, dates in UTC); the dataset type decides how they are stored.

## Source

[script.py](script.py)

The sample data in `sample-data/` is invented. `tests/kedro-project/` is a small Kedro project used by the tests: it removes cancelled orders and totals the rest per region against a target.
