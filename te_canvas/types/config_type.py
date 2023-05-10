from enum import Enum


class ConfigType(Enum):
    """
    The three different types of template configuration that exist.
    """

    TITLE = "title"
    LOCATION = "location"
    DESCRIPTION = "description"
