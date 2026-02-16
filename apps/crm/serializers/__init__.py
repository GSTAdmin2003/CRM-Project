# CRM Serializers Package

from .incoming_lead import (
    IncomingLeadCreateSerializer,
    IncomingLeadDetailSerializer,
    IncomingLeadListSerializer,
)
from .kanban import (
    KanbanDataSerializer,
    KanbanStageSerializer,
    UpdateLeadStageSerializer,
)
from .lead import (
    LeadCreateUpdateSerializer,
    LeadDetailSerializer,
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
    # Team serializers
    "SalesTeamListSerializer",
    "SalesTeamDetailSerializer",
    "SalesTeamCreateUpdateSerializer",
    # Stage serializers
    "LeadStageSerializer",
    "LeadStageCreateUpdateSerializer",
    # Incoming lead serializers
    "IncomingLeadListSerializer",
    "IncomingLeadDetailSerializer",
    "IncomingLeadCreateSerializer",
    # Kanban serializers
    "KanbanStageSerializer",
    "KanbanDataSerializer",
    "UpdateLeadStageSerializer",
]
