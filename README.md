# pytest-ruff

A pytest plugin to run [ruff](https://pypi.org/project/ruff/).

## Installation

```shell
pip install pytest-ruff
```

## Usage

```shell
pytest --ruff --ruff-format
```

The plugin will run one ruff check test per file and fail if code is not ok for ruff.

Format command only checks for format and fails for formatting errors.

## Configuration

You can override ruff configuration options by placing a `pyproject.toml` or `ruff.toml` file in your project directory, like when using standalone ruff.

## License

Distributed under the terms of the `MIT` license, `pytest-ruff` is free and open source software.
