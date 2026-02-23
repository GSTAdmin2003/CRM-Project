# CRM Serializers Package

from .kanban import (
    KanbanDataSerializer,
    KanbanStageSerializer,
    UpdateLeadStageSerializer,
)
from .lead import (
    LeadCreateUpdateSerializer,
    LeadDetailSerializer,
    LeadIncomingCreateSerializer,
    LeadListSerializer,
)
from .stage import (
    LeadStageCreateUpdateSerializer,
    LeadStageSerializer,
)
from .team import (
    SalesTeamCreateUpdateSerializer,
    SalesTeamDetailSerializer,
    SalesTeamListSerializer,
)

__all__ = [
    # Lead serializers
    "LeadListSerializer",
    "LeadDetailSerializer",
    "LeadCreateUpdateSerializer",
    "LeadIncomingCreateSerializer",
    # Team serializers
    "SalesTeamListSerializer",
    "SalesTeamDetailSerializer",
    "SalesTeamCreateUpdateSerializer",
    # Stage serializers
    "LeadStageSerializer",
    "LeadStageCreateUpdateSerializer",
    # Kanban serializers
    "KanbanStageSerializer",
    "KanbanDataSerializer",
    "UpdateLeadStageSerializer",
]
