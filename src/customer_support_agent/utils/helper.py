import logging
import os
from typing import List

logger = logging.getLogger(__name__)


def stringify_list(lst: List, sep: str = ", ") -> str:
    """return the joined elements of a list without the brackets []

    Args:
        lst (List): you data in a list
        sep (str, optional): a separator of your choosing. Defaults to ", ".

    Returns:
        List
    """
    return sep.join([str(i) for i in lst])


def enforce_dir(path: str) -> None:
    if not os.getcwd().endswith(path):
        os.chdir(path)
