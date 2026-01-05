from enum import Enum

class Services(str, Enum):
    """
    Enum representing various Bale services.
    """
    
    MESSAGING = "bale.messaging.v2.Messaging"
    """Represents the messaging service."""
    
    AUTH = "bale.auth.v1.Auth"
    """Represents the authentication service."""
    
    USER = "bale.users.v1.Users"
    """Represents the user management service."""
    
    PRESENCE = "bale.presence.v1.Presence"
    """Represents the presence service."""
    
    REPORT = "bale.report.v1.Report"
    """Represents the reporting service."""
    
    CONFIGS = "bale.v1.Configs"
    """Represents the configuration service."""
    
    ABACUS = "bale.abacus.v1.Abacus"
    """Represents the abacus service."""
    
    GROUPS = "bale.groups.v1.Groups"
    """Represents the groups management service."""
    
    FILES = "ai.bale.server.Files"
    """Represents the file management service."""
    
    GIFT_PACKET = "bale.giftpacket.v1.GiftPacket"
    """Represents the gift packet service."""
    
    KIFPOOL = "bale.kifpool.v1.Kifpool"
    """Represents the Kifpool service (financial pool management)."""
    
    MAGAZINE = "bale.magazine.v1.Magazine"
    """Represents the magazine content service."""
    
    POLL = "bale.poll.v1.Poll"
    """Represents the poll management service."""
