"""
Pydantic schemas for Evidence
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from pydantic import BaseModel, Field


class EvidenceMetadata(BaseModel):
    """Metadata for evidence submission."""
    test_type: Optional[str] = None
    location: Optional[str] = None
    inspector: Optional[str] = None
    equipment_id: Optional[str] = None
    additional_notes: Optional[str] = None


class EvidenceRead(BaseModel):
    """Schema for reading evidence metadata"""
    id: UUID = Field(
        ...,
        description="Unique identifier for the evidence"
    )
    session_id: UUID = Field(
        ...,
        description="Test session this evidence belongs to"
    )
    evidence_type: str = Field(
        ...,
        description="Type/category of evidence"
    )
    filename: Optional[str] = Field(
        None,
        description="Original filename of the evidence file"
    )
    file_type: Optional[str] = Field(
        None,
        description="MIME type of the evidence file"
    )
    file_size: Optional[int] = Field(
        None,
        description="Size of the evidence file in bytes"
    )
    hash: Optional[str] = Field(
        None,
        description="SHA-256 checksum for file integrity verification"
    )
    device_attestation_status: Optional[str] = Field(
        None,
        description="Device attestation verification status"
    )
    uploaded_at: datetime = Field(
        ...,
        description="When the evidence was uploaded"
    )
    flagged_for_review: bool = Field(
        ...,
        description="Whether evidence is flagged for review"
    )
    evidence_metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional metadata for the evidence"
    )

    class Config:
        from_attributes = True


class EvidenceDownloadResponse(BaseModel):
    """Response schema for evidence download URL"""
    download_url: str = Field(
        ...,
        description="Pre-signed S3 URL for downloading the evidence file"
    )
    expires_at: datetime = Field(
        ...,
        description="When the download URL expires"
    )


class EvidenceFlagRequest(BaseModel):
    """Request schema for flagging evidence"""
    flag_reason: str = Field(
        ...,
        min_length=1,
        description="Reason for flagging the evidence for review"
    )


class EvidenceFlagResponse(BaseModel):
    """Response schema for flagging evidence"""
    id: UUID = Field(
        ...,
        description="Evidence ID that was flagged"
    )
    flagged_for_review: bool = Field(
        ...,
        description="Updated flag status"
    )
    flag_reason: str = Field(
        ...,
        description="Reason for flagging"
    )
    flagged_at: datetime = Field(
        ...,
        description="When the evidence was flagged"
    )
    flagged_by: UUID = Field(
        ...,
        description="User who flagged the evidence"
    )

    class Config:
        from_attributes = True


class EvidenceLinkDefectRequest(BaseModel):
    """Request schema for linking evidence to defect"""
    defect_id: UUID = Field(
        ...,
        description="Defect ID to link the evidence to"
    )


class EvidenceResponse(BaseModel):
    """Response model for evidence submission."""
    evidence_id: str
    hash: str
    status: str
    message: Optional[str] = None
