from enum import Enum


class PollType(int, Enum):
    """
    Enum representing the types of polls in the system.
    """

    SINGLE_CHOICE = 0
    """
    Represents a single-choice poll where only one option can be selected.
    """

    MULTIPLE_CHOICE = 1
    """
    Represents a multiple-choice poll where multiple options can be selected.
    """
