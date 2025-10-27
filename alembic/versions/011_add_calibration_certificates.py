"""Add calibration certificates table

Revision ID: 011_add_calibration_certificates
Revises: 010_add_report_finalization_fields
Create Date: 2025-10-27

Implements AS 1851-2012 calibration tracking requirements.
All measurement instruments must have valid calibration certificates.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '011_add_calibration_certificates'
down_revision = '010_add_report_finalization_fields'
branch_labels = None
depends_on = None


def upgrade():
    """Create calibration certificates table"""
    op.create_table(
        'calibration_certificates',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, 
                 server_default=sa.text('uuid_generate_v4()')),
        sa.Column('instrument_id', sa.String(100), unique=True, nullable=False,
                 comment="Unique instrument identifier"),
        sa.Column('instrument_type', sa.String(50), nullable=False,
                 comment="Type: pressure_gauge, anemometer, force_meter"),
        sa.Column('cert_number', sa.String(100), nullable=False,
                 comment="Certificate number from calibration lab"),
        sa.Column('calibrated_date', sa.Date, nullable=False,
                 comment="Date of calibration"),
        sa.Column('expiry_date', sa.Date, nullable=False,
                 comment="Certificate expiry date"),
        sa.Column('cert_file_path', sa.Text, nullable=True,
                 comment="S3 path to certificate PDF"),
        sa.Column('calibration_lab', sa.String(255), nullable=True,
                 comment="Name of calibration laboratory"),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                 server_default=sa.func.now()),
        sa.Column('created_by', UUID(as_uuid=True), 
                 sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    )
    
    # Check constraint: expiry_date must be after calibrated_date
    op.create_check_constraint(
        'chk_calibration_dates',
        'calibration_certificates',
        'expiry_date > calibrated_date'
    )
    
    # Indexes for performance
    op.create_index('idx_calib_instrument', 'calibration_certificates', ['instrument_id'])
    op.create_index('idx_calib_expiry', 'calibration_certificates', ['expiry_date'])
    op.create_index('idx_calib_type', 'calibration_certificates', ['instrument_type'])


def downgrade():
    """Remove calibration certificates table"""
    op.drop_index('idx_calib_type', 'calibration_certificates')
    op.drop_index('idx_calib_expiry', 'calibration_certificates')
    op.drop_index('idx_calib_instrument', 'calibration_certificates')
    op.drop_constraint('chk_calibration_dates', 'calibration_certificates', type_='check')
    op.drop_table('calibration_certificates')
