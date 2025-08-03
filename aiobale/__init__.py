import warnings

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API.*",
    category=UserWarning,
    module="google.protobuf.*"
)

from .client.client import Client
from .dispatcher.dispatcher import Dispatcher
from .dispatcher.router import Router
from .utils.magic_filter import MagicFilter

F = MagicFilter()

__all__ = (
    "Client",
    "Dispatcher",
    "Router",
    "F"
)
