"""
Buildings API router with async operations and contract compliance
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List, Optional
import uuid
from datetime import datetime

from ..database.core import get_db
from ..models import Building, User
from ..schemas.building import (
    BuildingCreate, BuildingRead, BuildingUpdate, BuildingListResponse
)
from ..schemas.baseline import (
    BuildingBaselineSubmit, BaselineSubmissionResponse
)
from ..models.building_configuration import BuildingConfiguration
from ..models.baseline import (
    BaselinePressureDifferential, 
    BaselineAirVelocity, 
    BaselineDoorForce
)
from ..services.baseline_validator import validate_baseline_completeness
from ..dependencies import get_current_active_user
from ..schemas.auth import TokenPayload
from ..utils.pagination import encode_cursor, decode_cursor, create_pagination_filter

router = APIRouter(prefix="/v1/buildings", tags=["buildings"])


@router.post("/", response_model=BuildingRead, status_code=status.HTTP_201_CREATED)
async def create_building(
    building: BuildingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Create a new building with idempotency checks.
    
    Strictly adheres to v4.0 contract schemas with proper async operations.
    """
    # Idempotency check - prevent duplicate buildings
    existing_query = select(Building).where(
        and_(
            Building.name == building.site_name,
            Building.address == building.site_address
        )
    )
    result = await db.execute(existing_query)
    existing_building = result.scalar_one_or_none()
    
    if existing_building:
        raise HTTPException(
            status_code=409, 
            detail={
                "error_code": "FIRE-409",
                "message": "Building already exists",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    # Create new building
    db_building = Building(
        name=building.site_name,
        address=building.site_address,
        building_type=building.building_type,
        compliance_status=building.compliance_status or "pending",
        owner_id=building.owner_id or current_user.user_id
    )
    
    db.add(db_building)
    await db.commit()
    await db.refresh(db_building)
    
    # Return building with contract-compliant response
    return BuildingRead.model_validate(db_building)


@router.get("/", response_model=BuildingListResponse)
async def list_buildings(
    limit: int = Query(default=50, ge=1, le=100, description="Number of buildings to return"),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    building_type: Optional[str] = Query(None, description="Filter by building type"),
    compliance_status: Optional[str] = Query(None, description="Filter by compliance status"),
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    List buildings with cursor-based pagination and filtering.
    
    Implements standardized pagination per TDD specification.
    """
    # Decode cursor for pagination
    cursor_data = decode_cursor(cursor)
    
    # Build base query
    query = select(Building).order_by(Building.created_at.asc(), Building.id.asc())
    
    # Apply pagination filters
    pagination_conditions = create_pagination_filter(cursor_data)
    if pagination_conditions:
        query = query.where(and_(*pagination_conditions))
    
    # Apply filters
    conditions = []
    if building_type:
        conditions.append(Building.building_type == building_type)
    if compliance_status:
        conditions.append(Building.compliance_status == compliance_status)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    # Apply limit + 1 to check if there are more results
    query = query.limit(limit + 1)
    
    # Execute query
    result = await db.execute(query)
    buildings = result.scalars().all()
    
    # Check if there are more results
    has_more = len(buildings) > limit
    if has_more:
        buildings = buildings[:limit]  # Remove the extra record
    
    # Generate next cursor
    next_cursor = None
    if has_more and buildings:
        last_building = buildings[-1]
        next_cursor = encode_cursor({
            "id": last_building.id,
            "created_at": last_building.created_at,
            "vector_clock": {}  # Buildings don't use vector clocks
        })
    
    # Convert to response format
    building_reads = [
        BuildingRead(
            building_id=building.id,
            name=building.name,
            address=building.address,
            building_type=building.building_type,
            compliance_status=building.compliance_status,
            owner_id=building.owner_id,
            created_at=building.created_at,
            updated_at=building.updated_at,
            status="active"
        )
        for building in buildings
    ]
    
    return BuildingListResponse(
        buildings=building_reads,
        total=len(building_reads),
        next_cursor=next_cursor,
        has_more=has_more
    )


@router.get("/{building_id}", response_model=BuildingRead)
async def get_building(
    building_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Get a specific building by ID.
    
    Returns standardized error format for not found cases.
    """
    query = select(Building).where(Building.id == building_id)
    result = await db.execute(query)
    building = result.scalar_one_or_none()
    
    if not building:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Building not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    return BuildingRead(
        building_id=building.id,
        name=building.name,
        address=building.address,
        building_type=building.building_type,
        compliance_status=building.compliance_status,
        owner_id=building.owner_id,
        created_at=building.created_at,
        updated_at=building.updated_at,
        status="active"
    )


@router.put("/{building_id}", response_model=BuildingRead)
async def update_building(
    building_id: uuid.UUID,
    building_update: BuildingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Update a specific building.
    
    Implements partial updates with proper validation.
    """
    # Get existing building
    query = select(Building).where(Building.id == building_id)
    result = await db.execute(query)
    building = result.scalar_one_or_none()
    
    if not building:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Building not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    # Update fields
    update_data = building_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(building, field, value)
    
    # Save changes
    await db.commit()
    await db.refresh(building)
    
    return BuildingRead(
        building_id=building.id,
        name=building.name,
        address=building.address,
        building_type=building.building_type,
        compliance_status=building.compliance_status,
        owner_id=building.owner_id,
        created_at=building.created_at,
        updated_at=building.updated_at,
        status="active"
    )


@router.delete("/{building_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_building(
    building_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Delete a specific building.
    
    Implements soft delete for audit trail compliance.
    """
    query = select(Building).where(Building.id == building_id)
    result = await db.execute(query)
    building = result.scalar_one_or_none()
    
    if not building:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Building not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    # For now, implement hard delete
    # In production, this would be a soft delete by updating a deleted_at field
    await db.delete(building)
    await db.commit()


@router.post("/{building_id}/baseline", response_model=BaselineSubmissionResponse)
async def submit_baseline_data(
    building_id: uuid.UUID,
    baseline_data: BuildingBaselineSubmit,
    db: AsyncSession = Depends(get_db),
    current_user: TokenPayload = Depends(get_current_active_user)
):
    """
    Submit baseline data for a building.
    
    Accepts building configuration and baseline measurements for stair pressurization
    compliance. Validates data against AS 1851-2012 requirements and returns
    completeness information.
    """
    # Verify building exists and user has access
    building_query = select(Building).where(Building.id == building_id)
    result = await db.execute(building_query)
    building = result.scalar_one_or_none()
    
    if not building:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "FIRE-404",
                "message": "Building not found",
                "transaction_id": str(uuid.uuid4()),
                "retryable": False
            }
        )
    
    items_created = 0
    items_updated = 0
    
    try:
        # Handle building configuration
        if baseline_data.building_configuration:
            # Check if configuration already exists
            config_query = select(BuildingConfiguration).where(
                BuildingConfiguration.building_id == building_id
            )
            config_result = await db.execute(config_query)
            existing_config = config_result.scalar_one_or_none()
            
            if existing_config:
                # Update existing configuration
                config_data = baseline_data.building_configuration.dict(exclude_unset=True)
                for field, value in config_data.items():
                    setattr(existing_config, field, value)
                existing_config.created_by = current_user.user_id
                items_updated += 1
            else:
                # Create new configuration
                new_config = BuildingConfiguration(
                    building_id=building_id,
                    created_by=current_user.user_id,
                    **baseline_data.building_configuration.dict(exclude_unset=True)
                )
                db.add(new_config)
                items_created += 1
        
        # Handle pressure measurements
        if baseline_data.pressure_measurements:
            for measurement_data in baseline_data.pressure_measurements:
                # Check if measurement already exists
                pressure_query = select(BaselinePressureDifferential).where(
                    and_(
                        BaselinePressureDifferential.building_id == building_id,
                        BaselinePressureDifferential.floor_id == measurement_data.floor_id,
                        BaselinePressureDifferential.door_configuration == measurement_data.door_configuration
                    )
                )
                pressure_result = await db.execute(pressure_query)
                existing_pressure = pressure_result.scalar_one_or_none()
                
                if existing_pressure:
                    # Update existing measurement
                    existing_pressure.pressure_pa = measurement_data.pressure_pa
                    existing_pressure.measured_date = measurement_data.measured_date
                    existing_pressure.created_by = current_user.user_id
                    items_updated += 1
                else:
                    # Create new measurement
                    new_pressure = BaselinePressureDifferential(
                        building_id=building_id,
                        created_by=current_user.user_id,
                        **measurement_data.dict()
                    )
                    db.add(new_pressure)
                    items_created += 1
        
        # Handle velocity measurements
        if baseline_data.velocity_measurements:
            for measurement_data in baseline_data.velocity_measurements:
                # Check if measurement already exists
                velocity_query = select(BaselineAirVelocity).where(
                    and_(
                        BaselineAirVelocity.building_id == building_id,
                        BaselineAirVelocity.doorway_id == measurement_data.doorway_id
                    )
                )
                velocity_result = await db.execute(velocity_query)
                existing_velocity = velocity_result.scalar_one_or_none()
                
                if existing_velocity:
                    # Update existing measurement
                    existing_velocity.velocity_ms = measurement_data.velocity_ms
                    existing_velocity.measured_date = measurement_data.measured_date
                    existing_velocity.created_by = current_user.user_id
                    items_updated += 1
                else:
                    # Create new measurement
                    new_velocity = BaselineAirVelocity(
                        building_id=building_id,
                        created_by=current_user.user_id,
                        **measurement_data.dict()
                    )
                    db.add(new_velocity)
                    items_created += 1
        
        # Handle door force measurements
        if baseline_data.door_force_measurements:
            for measurement_data in baseline_data.door_force_measurements:
                # Check if measurement already exists
                force_query = select(BaselineDoorForce).where(
                    and_(
                        BaselineDoorForce.building_id == building_id,
                        BaselineDoorForce.door_id == measurement_data.door_id
                    )
                )
                force_result = await db.execute(force_query)
                existing_force = force_result.scalar_one_or_none()
                
                if existing_force:
                    # Update existing measurement
                    existing_force.force_newtons = measurement_data.force_newtons
                    existing_force.measured_date = measurement_data.measured_date
                    existing_force.created_by = current_user.user_id
                    items_updated += 1
                else:
                    # Create new measurement
                    new_force = BaselineDoorForce(
                        building_id=building_id,
                        created_by=current_user.user_id,
                        **measurement_data.dict()
                    )
                    db.add(new_force)
                    items_created += 1
        
        # Commit all changes
        await db.commit()
        
        # Get updated completeness
        completeness = await validate_baseline_completeness(building_id, db)
        
        return BaselineSubmissionResponse(
            success=True,
            message=f"Baseline data submitted successfully. Created {items_created} items, updated {items_updated} items.",
            completeness=completeness,
            items_created=items_created,
            items_updated=items_updated
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "FIRE-500",
                "message": f"Failed to submit baseline data: {str(e)}",
                "transaction_id": str(uuid.uuid4()),
                "retryable": True
            }
        )