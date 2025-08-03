from ...enums import Services
from ...types.responses import DefaultResponse
from ..base import BaleMethod


class SignOut(BaleMethod):
    __service__ = Services.AUTH.value
    __method__ = "SignOut"
    
    __returning__ = DefaultResponse
