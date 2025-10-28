"""
Baseline measurement service for C&E testing.

Handles establishment and retrieval of baseline measurements per AS 1851-2012.
First inspection establishes baseline; future tests compare against it.
"""

from typing import Dict, Any, Optional, List
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from ..models.baseline import (
    BaselinePressureDifferential,
    BaselineAirVelocity,
    BaselineDoorForce,
)

logger = logging.getLogger(__name__)


class BaselineService:
    """
    Manages baseline measurements for C&E testing.

    AS 1851-2012 Requirements:
    - First inspection establishes baseline
    - Store per building: pressure, velocity, force
    - Future tests compare against baseline
    """

    async def get_baseline(
        self, building_id: str, db: AsyncSession
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve baseline measurements for a building.

        Args:
            building_id: Building UUID
            db: Database session

        Returns:
            Dict with baseline data or None if not established
        """
        # Fetch baseline records
        pressure_result = await db.execute(
            select(BaselinePressureDifferential)
            .where(BaselinePressureDifferential.building_id == building_id)
            .limit(1)
        )
        pressure_baseline = pressure_result.scalar_one_or_none()

        velocity_result = await db.execute(
            select(BaselineAirVelocity)
            .where(BaselineAirVelocity.building_id == building_id)
            .limit(1)
        )
        velocity_baseline = velocity_result.scalar_one_or_none()

        force_result = await db.execute(
            select(BaselineDoorForce)
            .where(BaselineDoorForce.building_id == building_id)
            .limit(1)
        )
        force_baseline = force_result.scalar_one_or_none()

        # Return None if no baseline exists
        if not (pressure_baseline or velocity_baseline or force_baseline):
            return None

        # Build baseline dict
        baseline = {}

        if pressure_baseline:
            baseline["pressure"] = {
                "value": pressure_baseline.pressure_pa,
                "unit": "Pa",
                "measured_date": pressure_baseline.measured_date.isoformat(),
            }

        if velocity_baseline:
            baseline["velocity"] = {
                "value": velocity_baseline.velocity_ms,
                "unit": "m/s",
                "measured_date": velocity_baseline.measured_date.isoformat(),
            }

        if force_baseline:
            baseline["force"] = {
                "value": force_baseline.force_newtons,
                "unit": "N",
                "measured_date": force_baseline.measured_date.isoformat(),
            }

        return baseline

    async def establish_baseline(
        self,
        building_id: str,
        measurements: Dict[str, float],
        created_by: Optional[str],
        db: AsyncSession,
        location_ids: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """
        Establish baseline from first inspection measurements.

        Args:
            building_id: Building UUID
            measurements: Dict with keys: pressure, velocity, force
            created_by: User UUID who created baseline
            db: Database session
            location_ids: Optional dict with keys: floor_id, doorway_id, door_id

        Returns:
            Established baseline data
        """
        measured_date = date.today()
        baseline = {}

        # Use provided location IDs or fall back to generic defaults
        location_ids = location_ids or {}
        floor_id = location_ids.get("floor_id", "all_floors")
        doorway_id = location_ids.get("doorway_id", "main_exit")
        door_id = location_ids.get("door_id", "fire_exit_1")

        # Create pressure baseline
        if "pressure" in measurements:
            pressure_baseline = BaselinePressureDifferential(
                building_id=building_id,
                floor_id=floor_id,
                door_configuration="all_doors_closed",
                pressure_pa=measurements["pressure"],
                measured_date=measured_date,
                created_by=created_by,
            )
            db.add(pressure_baseline)
            baseline["pressure"] = {
                "value": measurements["pressure"],
                "unit": "Pa",
                "measured_date": measured_date.isoformat(),
            }

        # Create velocity baseline
        if "velocity" in measurements:
            velocity_baseline = BaselineAirVelocity(
                building_id=building_id,
                doorway_id=doorway_id,
                velocity_ms=measurements["velocity"],
                measured_date=measured_date,
                created_by=created_by,
            )
            db.add(velocity_baseline)
            baseline["velocity"] = {
                "value": measurements["velocity"],
                "unit": "m/s",
                "measured_date": measured_date.isoformat(),
            }

        # Create force baseline
        if "force" in measurements:
            force_baseline = BaselineDoorForce(
                building_id=building_id,
                door_id=door_id,
                force_newtons=measurements["force"],
                measured_date=measured_date,
                created_by=created_by,
            )
            db.add(force_baseline)
            baseline["force"] = {
                "value": measurements["force"],
                "unit": "N",
                "measured_date": measured_date.isoformat(),
            }

        await db.commit()

        logger.info(f"Baseline established for building {building_id}: {baseline}")

        return baseline

    @staticmethod
    def extract_measurements_from_session(measurements: List[Any]) -> Dict[str, float]:
        """
        Extract baseline measurements from C&E test measurements.

        Args:
            measurements: List of CETestMeasurement objects

        Returns:
            Dict with keys: pressure, velocity, force and their values
        """
        measurement_values = {}
        for measurement in measurements:
            mtype = measurement.measurement_type.lower()
            if "pressure" in mtype:
                measurement_values["pressure"] = measurement.measurement_value
            elif "velocity" in mtype:
                measurement_values["velocity"] = measurement.measurement_value
            elif "force" in mtype:
                measurement_values["force"] = measurement.measurement_value
        return measurement_values


# Singleton instance
baseline_service = BaselineService()
