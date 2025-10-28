"""
Background worker to monitor critical defects and enforce 24-hour notification SLA.

References:
- AS 1851-2012: Section 8.3 - Critical defect notification requirements
- data_model.md: defects table schema with severity tracking
- AGENTS.md: Security gate (parameterized queries, no secrets in logs)
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.dialects.postgresql import UUID

from ..models.defects import Defect
from ..models.test_sessions import TestSession
from ..services.notification_service import notification_service
from ..database.core import AsyncSessionLocal

logger = logging.getLogger(__name__)


class DefectMonitor:
    """
    Monitor defects for critical severity and trigger notifications per AS 1851-2012 SLA.
    
    SLA Requirements:
    - Notifications sent within 24 hours of critical defect detection
    - Automatic monitoring at configured intervals
    - Tracks notification status to prevent duplicates
    
    References: AS 1851-2012 Section 8.3 - Critical Defect Notification
    """
    
    def __init__(self):
        """Initialize defect monitor with configuration from environment."""
        self.check_interval_seconds = int(
            os.getenv('DEFECT_MONITOR_INTERVAL', '3600')  # Default: 1 hour
        )
        self.notification_sla_hours = 24
        self.enabled = os.getenv('DEFECT_MONITOR_ENABLED', 'true').lower() == 'true'
        
        logger.info(
            f"Defect monitor initialized: "
            f"enabled={self.enabled}, "
            f"check_interval={self.check_interval_seconds}s, "
            f"sla={self.notification_sla_hours}h"
        )
    
    async def run(self):
        """
        Main monitoring loop.
        
        Runs continuously in background, checking for critical defects
        at configured intervals and sending notifications as needed.
        """
        if not self.enabled:
            logger.info("Defect monitor disabled via configuration")
            return
        
        logger.info("Defect monitor started - monitoring for critical defects")
        
        while True:
            try:
                await self._check_for_critical_defects()
                await asyncio.sleep(self.check_interval_seconds)
            
            except asyncio.CancelledError:
                logger.info("Defect monitor cancelled - shutting down")
                break
            
            except Exception as e:
                logger.error(f"Defect monitor error: {e}", exc_info=True)
                # Wait before retrying on error
                await asyncio.sleep(60)
    
    async def _check_for_critical_defects(self):
        """
        Check for unnotified critical defects within SLA window.
        
        Finds defects that are:
        - Severity = "critical"
        - Status = "open" or "acknowledged" (not yet resolved)
        - Discovered within the last 24 hours (SLA window)
        - No notification sent yet
        
        Sends notifications for each matching defect.
        """
        async with AsyncSessionLocal() as db:
            try:
                # Calculate SLA window
                sla_cutoff = datetime.now(timezone.utc) - timedelta(
                    hours=self.notification_sla_hours
                )
                
                # Find critical defects needing notification
                # Query defects table for critical severity
                result = await db.execute(
                    select(Defect)
                    .where(
                        and_(
                            Defect.severity == 'critical',
                            or_(
                                Defect.status == 'open',
                                Defect.status == 'acknowledged'
                            ),
                            Defect.discovered_at > sla_cutoff,  # Within SLA window
                        )
                    )
                )
                
                defects = result.scalars().all()
                
                # Filter out already notified defects
                # Check if notification was sent by querying test_session.session_data
                unnotified_defects = []
                for defect in defects:
                    # Get associated test session
                    session_result = await db.execute(
                        select(TestSession).where(TestSession.id == defect.test_session_id)
                    )
                    session = session_result.scalar_one_or_none()
                    
                    if session:
                        session_data = session.session_data or {}
                        notifications = session_data.get('critical_defect_notifications', {})
                        defect_key = str(defect.id)
                        
                        # Check if this defect was already notified
                        if defect_key not in notifications:
                            unnotified_defects.append((defect, session))
                
                logger.info(
                    f"Defect monitor check: found {len(defects)} critical defects, "
                    f"{len(unnotified_defects)} need notification"
                )
                
                # Process each unnotified defect
                for defect, session in unnotified_defects:
                    await self._process_critical_defect(defect, session, db)
            
            except Exception as e:
                logger.error(f"Error checking for critical defects: {e}", exc_info=True)
                raise
    
    async def _process_critical_defect(
        self,
        defect: Defect,
        session: TestSession,
        db: AsyncSession
    ):
        """
        Process a critical defect and send notification.
        
        Args:
            defect: Defect instance with severity="critical"
            session: Associated TestSession
            db: Database session
        """
        try:
            # Build defect details for notification
            defect_details = {
                "defect_id": str(defect.id),
                "location": self._extract_location(defect),
                "severity": defect.severity,
                "category": defect.category or "unspecified",
                "description": defect.description,
                "as1851_rule_code": defect.as1851_rule_code or "N/A",
                "discovered_at": defect.discovered_at.isoformat(),
                "remediation_timeline": self._determine_remediation_timeline(defect),
                "technical_details": self._build_technical_details(defect)
            }
            
            # Determine defect type for notification
            defect_type = self._map_category_to_type(defect.category)
            
            # Send notification
            notification_result = await notification_service.notify_critical_defect(
                building_id=str(defect.building_id),
                defect_type=defect_type,
                defect_details=defect_details,
                db=db
            )
            
            # Update test session to mark defect as notified
            session_data = session.session_data or {}
            if 'critical_defect_notifications' not in session_data:
                session_data['critical_defect_notifications'] = {}
            
            session_data['critical_defect_notifications'][str(defect.id)] = {
                "notification_id": notification_result['notification_id'],
                "sent_at": notification_result['sent_at'],
                "email_status": notification_result['email_status'],
                "owner_email": notification_result['owner_email']
            }
            
            session.session_data = session_data
            await db.commit()
            
            logger.info(
                f"Critical defect notification sent: "
                f"defect_id={defect.id}, "
                f"building_id={defect.building_id}, "
                f"notification_id={notification_result['notification_id']}"
            )
        
        except Exception as e:
            logger.error(
                f"Failed to process critical defect {defect.id}: {e}",
                exc_info=True
            )
            # Don't raise - continue processing other defects
    
    def _extract_location(self, defect: Defect) -> str:
        """
        Extract human-readable location from defect data.
        
        Args:
            defect: Defect instance
        
        Returns:
            Location string
        """
        # Try to parse location from description or metadata
        if defect.description and "location:" in defect.description.lower():
            # Extract location from description
            parts = defect.description.split("location:", 1)
            if len(parts) > 1:
                location = parts[1].split("\n")[0].strip()
                return location[:100]  # Limit length
        
        # Default fallback
        return "See inspection report for location details"
    
    def _determine_remediation_timeline(self, defect: Defect) -> str:
        """
        Determine remediation timeline based on defect severity and category.
        
        Args:
            defect: Defect instance
        
        Returns:
            Remediation timeline string
        """
        if defect.severity == 'critical':
            # Critical defects need immediate attention
            if defect.category in ['EXIT_BLOCKED', 'DETECTION_FAILURE', 'ALARM_FAILURE']:
                return "Immediate (within 4 hours)"
            else:
                return "Urgent (within 24 hours)"
        
        return "24-48 hours"
    
    def _build_technical_details(self, defect: Defect) -> str:
        """
        Build technical details string for notification.
        
        Args:
            defect: Defect instance
        
        Returns:
            Technical details string
        """
        details = []
        
        if defect.as1851_rule_code:
            details.append(f"AS 1851 Rule: {defect.as1851_rule_code}")
        
        if defect.category:
            details.append(f"Category: {defect.category}")
        
        if defect.asset_id:
            details.append(f"Asset ID: {defect.asset_id}")
        
        details.append(f"Defect ID: {defect.id}")
        details.append(f"Test Session: {defect.test_session_id}")
        
        return " | ".join(details)
    
    def _map_category_to_type(self, category: Optional[str]) -> str:
        """
        Map defect category to notification defect type.
        
        Args:
            category: Defect category string
        
        Returns:
            Defect type code for notification
        """
        category_map = {
            "extinguisher_pressure": "PRESSURE_OUT_OF_RANGE",
            "exit_blocked": "EXIT_BLOCKED",
            "detection_failure": "DETECTION_FAILURE",
            "hydrant_pressure": "HYDRANT_PRESSURE_LOW",
            "extinguisher_missing": "EXTINGUISHER_MISSING",
            "hose_reel_damaged": "HOSE_REEL_DAMAGED",
            "alarm_failure": "ALARM_FAILURE"
        }
        
        return category_map.get(category, "CRITICAL_DEFECT_DETECTED")


# Singleton instance
defect_monitor = DefectMonitor()


async def start_defect_monitor():
    """
    Start the defect monitor as a background task.
    
    Called from main.py on application startup.
    Creates an asyncio task that runs the monitor continuously.
    
    Returns:
        asyncio.Task: The background task
    """
    task = asyncio.create_task(defect_monitor.run())
    logger.info("Defect monitor background task started")
    return task
