"""Compliance workflow models"""

import uuid
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from ..database.core import Base


class ComplianceWorkflow(Base):
    """Workflow templates for compliance evidence flows"""

    __tablename__ = 'compliance_workflows'

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )

    name = Column(String(255), nullable=False, doc="Workflow name")
    description = Column(Text, nullable=True, doc="Workflow description")
    compliance_standard = Column(
        String(100),
        nullable=False,
        default='AS1851-2012',
        server_default='AS1851-2012',
        doc="Compliance standard key"
    )

    workflow_definition = Column(
        JSONB,
        nullable=False,
        doc="Serialized workflow graph (nodes, edges)"
    )

    status = Column(
        String(50),
        nullable=False,
        server_default='draft',
        doc="draft | active | archived"
    )
    is_template = Column(
        Boolean,
        nullable=False,
        server_default='false',
        doc="Whether the workflow is reusable"
    )

    created_by = Column(
        UUID(as_uuid=True),
        ForeignKey('users.id'),
        nullable=False,
        doc="Author of the workflow"
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="Creation timestamp"
    )
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        doc="Last update timestamp"
    )

    instances = relationship(
        'ComplianceWorkflowInstance',
        back_populates='workflow',
        cascade='all, delete-orphan'
    )

    def __repr__(self) -> str:
        return f"<ComplianceWorkflow(id={self.id}, name='{self.name}', status='{self.status}')>"


class ComplianceWorkflowInstance(Base):
    """Active execution of a compliance workflow"""

    __tablename__ = 'compliance_workflow_instances'

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.uuid_generate_v4()
    )

    workflow_id = Column(
        UUID(as_uuid=True),
        ForeignKey('compliance_workflows.id'),
        nullable=False,
        doc="Template identifier"
    )
    building_id = Column(
        UUID(as_uuid=True),
        ForeignKey('buildings.id'),
        nullable=False,
        doc="Target building"
    )

    current_node_id = Column(
        String(255),
        nullable=True,
        doc="Current node identifier"
    )
    instance_data = Column(
        JSONB,
        nullable=False,
        default=dict,
        doc="Execution state payload"
    )

    status = Column(
        String(50),
        nullable=False,
        server_default='active',
        doc="active | completed | failed | paused"
    )

    started_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        doc="When the instance started"
    )
    completed_at = Column(
        DateTime(timezone=True),
        nullable=True,
        doc="Completion timestamp"
    )

    workflow = relationship('ComplianceWorkflow', back_populates='instances')
    building = relationship('Building')

    def __repr__(self) -> str:
        return (
            f"<ComplianceWorkflowInstance(id={self.id}, workflow_id={self.workflow_id}, "
            f"status='{self.status}')>"
        )
