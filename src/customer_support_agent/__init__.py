from importlib.metadata import version, PackageNotFoundError

from customer_support_agent import utils
from customer_support_agent.agent import run_agent

try:
    __version__ = version("customer-support-agent")
except PackageNotFoundError:
    # Package not installed (running from source during development)
    __version__ = "0.1.0"

__all__ = [
    "__version__",
    "utils",
    "run_agent",
]
