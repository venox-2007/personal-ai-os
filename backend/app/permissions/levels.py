"""Permission levels and security hierarchy for Personal AI OS."""

from enum import IntEnum
from typing import Dict, Any


class PermissionLevel(IntEnum):
    """Hierarchical permission levels for tools and actions.

    LEVEL_0_READ_ONLY (0):
        Safe inspection actions with zero side effects.
        Examples: Search Gmail, read emails, query calendar, read files.

    LEVEL_1_LOW_IMPACT (1):
        Local or non-destructive staging actions.
        Examples: Create draft email, create calendar event, add tag/label.

    LEVEL_2_EXTERNAL_SIDE_EFFECT (2):
        Actions with real-world or external effects.
        Requires explicit human confirmation by default.
        Examples: Send email, post to GitHub, overwrite non-critical files.

    LEVEL_3_DESTRUCTIVE (3):
        Irreversible or high-risk actions.
        Always requires explicit human confirmation.
        Examples: Delete emails, delete files, bulk modifications, wipe memory.
    """

    LEVEL_0_READ_ONLY = 0
    LEVEL_1_LOW_IMPACT = 1
    LEVEL_2_EXTERNAL_SIDE_EFFECT = 2
    LEVEL_3_DESTRUCTIVE = 3

    @property
    def label(self) -> str:
        """Returns a human-readable title for the permission level."""
        labels = {
            0: "Read-only",
            1: "Low Impact",
            2: "External Side Effect",
            3: "Destructive",
        }
        return labels.get(self.value, "Unknown")

    @property
    def requires_approval_default(self) -> bool:
        """Whether this level requires human-in-the-loop approval by default."""
        return self.value >= PermissionLevel.LEVEL_2_EXTERNAL_SIDE_EFFECT

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.value,
            "name": self.name,
            "label": self.label,
            "requires_approval": self.requires_approval_default,
        }
