import os
import pathlib
import sys
import tomllib

MODULE_DIR = os.path.abspath(pathlib.Path("./src"))
sys.path.append(MODULE_DIR)

import logging

import pytest
import yaml
import dotenv

logger = logging.getLogger(__name__)


@pytest.fixture
def test_param_dict():
    with open(pathlib.Path("./tests/test_params.yml")) as f:
        return yaml.safe_load(f)


@pytest.fixture
def secrets():
    return dotenv.dotenv_values(dotenv_path=".env")


@pytest.fixture
def pyproject_version():
    """Get version from pyproject.toml (single source of truth)"""
    with open(pathlib.Path("./pyproject.toml"), "rb") as f:
        pyproject = tomllib.load(f)
    return pyproject["project"]["version"]
