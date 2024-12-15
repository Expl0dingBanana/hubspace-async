"""Generic/base Resource Model(s)."""

from enum import Enum


class ResourceTypes(Enum):
    """
    Type of the supported resources
    """

    DEVICE = "metadevice.device"
    HOME = "metadata.home"
    ROOM = "metadata.room"
    FAN = "fan"
    LIGHT = "light"
    UNKNOWN = "unknown"

    @classmethod
    def _missing_(cls: type, value: object):  # noqa: ARG003
        """Set default enum member if an unknown value is provided."""
        return ResourceTypes.UNKNOWN
