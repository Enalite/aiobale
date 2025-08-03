from ...enums import Services
from ...types.responses import DefaultResponse
from ..base import BaleMethod


class SignOut(BaleMethod):
    """
    Represents the 'SignOut' API method to log out the current user.

    This method calls the authentication service to sign out the user session.

    Returns:
        aiobale.types.responses.DefaultResponse: The standard response.
    """
    __service__ = Services.AUTH.value
    __method__ = "SignOut"
    
    __returning__ = DefaultResponse
