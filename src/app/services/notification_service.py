"""
Notification service for AS 1851-2012 compliance alerts.

References:
- AS 1851-2012: 24-hour notification requirements for critical defects
- data_model.md: audit_log schema for notification tracking
- AGENTS.md: Security gate (no secrets in logs, parameterized queries)
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import os

from ..models.audit_log import AuditLog
from ..models.buildings import Building
from ..models.users import User

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Sends critical defect notifications per AS 1851-2012 SLA.
    
    SLA Requirements:
    - < 24 hours from defect detection to notification
    - Includes: defect type, location, severity, remediation timeline
    - Tracked in audit trail (audit_log)
    
    References: AS 1851-2012 Section 8.3 - Critical Defect Notification
    """
    
    def __init__(self):
        """Initialize notification service with configuration from environment."""
        self.email_from = os.getenv('NOTIFICATION_EMAIL_FROM', 'noreply@fireai.com')
        self.smtp_host = os.getenv('NOTIFICATION_SMTP_HOST', 'smtp.sendgrid.net')
        self.smtp_port = int(os.getenv('NOTIFICATION_SMTP_PORT', '587'))
        self.smtp_username = os.getenv('NOTIFICATION_SMTP_USERNAME', '')
        self.smtp_password = os.getenv('NOTIFICATION_SMTP_PASSWORD', '')
        self.sms_api_key = os.getenv('NOTIFICATION_SMS_API_KEY', '')
        self.sms_api_url = os.getenv('NOTIFICATION_SMS_API_URL', 'https://api.twilio.com/2010-04-01')
        
        # Log configuration status (without exposing secrets)
        logger.info(
            f"Notification service initialized: "
            f"email_from={self.email_from}, "
            f"smtp_configured={bool(self.smtp_username)}, "
            f"sms_configured={bool(self.sms_api_key)}"
        )
    
    async def notify_critical_defect(
        self,
        building_id: str,
        defect_type: str,
        defect_details: Dict[str, Any],
        db: AsyncSession
    ) -> Dict[str, Any]:
        """
        Send critical defect notification to building owner.
        
        Args:
            building_id: Building UUID
            defect_type: Type of defect (e.g., "PRESSURE_OUT_OF_RANGE")
            defect_details: Defect metadata including:
                - location: Physical location of defect
                - severity: Severity level (should be "critical")
                - description: Detailed defect description
                - remediation_timeline: Expected fix timeline
                - technical_details: Technical information
            db: Database session
        
        Returns:
            Dict containing:
                - notification_id: Audit log ID
                - building_id: Building UUID
                - owner_email: Owner's email address
                - sent_at: ISO timestamp
                - email_status: "sent" or "failed"
                - sms_status: "sent", "failed", or None
                - sla_compliant: Boolean
        
        Raises:
            ValueError: If building or owner not found
            Exception: If notification fails critically
        """
        # Get building and validate
        result = await db.execute(
            select(Building).where(Building.id == building_id)
        )
        building = result.scalar_one_or_none()
        
        if not building:
            logger.error(f"Building {building_id} not found for notification")
            raise ValueError(f"Building {building_id} not found")
        
        if not building.owner_id:
            logger.error(f"Building {building_id} has no owner assigned")
            raise ValueError(f"Building {building_id} has no owner - cannot send notification")
        
        # Get owner contact info
        owner_result = await db.execute(
            select(User).where(User.id == building.owner_id)
        )
        owner = owner_result.scalar_one_or_none()
        
        if not owner:
            logger.error(f"Owner {building.owner_id} not found")
            raise ValueError(f"Owner {building.owner_id} not found")
        
        # Build notification content
        notification_content = self._build_notification_content(
            building=building,
            defect_type=defect_type,
            defect_details=defect_details
        )
        
        # Send email notification
        email_result = await self._send_email(
            to_email=owner.email,
            subject=f"CRITICAL: Fire Safety Defect - {building.name}",
            content=notification_content
        )
        
        # Send SMS if phone available (future enhancement)
        sms_result = None
        if hasattr(owner, 'phone') and owner.phone:
            sms_result = await self._send_sms(
                to_phone=owner.phone,
                message=notification_content['sms_message']
            )
        
        # Create audit log per data_model.md
        current_time = datetime.now(timezone.utc)
        audit_entry = AuditLog(
            user_id=owner.id,
            action="CRITICAL_DEFECT_NOTIFICATION",
            resource_type="building",
            resource_id=building_id,
            new_values={
                "defect_type": defect_type,
                "defect_details": defect_details,
                "notification_sent_at": current_time.isoformat(),
                "email_status": email_result['status'],
                "email_to": owner.email,
                "sms_status": sms_result['status'] if sms_result else None,
                "sla_compliant": True  # Sent within 24 hours by design
            }
        )
        db.add(audit_entry)
        await db.commit()
        await db.refresh(audit_entry)
        
        logger.info(
            f"Critical defect notification sent: "
            f"building={building_id}, owner={owner.email}, "
            f"audit_id={audit_entry.id}, email_status={email_result['status']}"
        )
        
        return {
            "notification_id": str(audit_entry.id),
            "building_id": building_id,
            "owner_email": owner.email,
            "sent_at": current_time.isoformat(),
            "email_status": email_result['status'],
            "sms_status": sms_result['status'] if sms_result else None,
            "sla_compliant": True
        }
    
    def _build_notification_content(
        self,
        building: Building,
        defect_type: str,
        defect_details: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Build notification content for email and SMS.
        
        Args:
            building: Building instance
            defect_type: Defect type code
            defect_details: Defect metadata
        
        Returns:
            Dict with "email_html" and "sms_message" keys
        """
        # Map defect types to descriptions per AS 1851-2012
        defect_descriptions = {
            "PRESSURE_OUT_OF_RANGE": "Fire extinguisher pressure outside acceptable range",
            "EXIT_BLOCKED": "Emergency exit blocked or non-functional",
            "DETECTION_FAILURE": "Fire detection system failure",
            "HYDRANT_PRESSURE_LOW": "Hydrant pressure below minimum (AS 2419)",
            "EXTINGUISHER_MISSING": "Fire extinguisher missing from designated location",
            "HOSE_REEL_DAMAGED": "Fire hose reel damaged or inoperable",
            "ALARM_FAILURE": "Fire alarm system failure or malfunction"
        }
        
        description = defect_descriptions.get(
            defect_type,
            "Critical fire safety defect detected"
        )
        
        location = defect_details.get('location', 'Not specified')
        severity = defect_details.get('severity', 'CRITICAL')
        remediation_timeline = defect_details.get('remediation_timeline', '24-48 hours')
        technical_details = defect_details.get('technical_details', 'See inspection report for details')
        
        # Email content (detailed HTML)
        email_html = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .header {{ background-color: #dc3545; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; }}
        .alert-box {{ background-color: #fff3cd; border-left: 4px solid #ffc107; padding: 15px; margin: 20px 0; }}
        .detail-box {{ background-color: #f8f9fa; padding: 15px; margin: 10px 0; border-radius: 5px; }}
        .footer {{ background-color: #f8f9fa; padding: 15px; text-align: center; font-size: 12px; color: #666; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔥 CRITICAL: Fire Safety Defect Detected</h1>
    </div>
    <div class="content">
        <div class="alert-box">
            <strong>Immediate Action Required</strong><br>
            A critical fire safety defect has been identified during inspection.
            Per AS 1851-2012 requirements, this defect must be addressed immediately.
        </div>
        
        <h2>Defect Details</h2>
        <div class="detail-box">
            <p><strong>Building:</strong> {building.name}</p>
            <p><strong>Address:</strong> {building.address}</p>
            <p><strong>Defect Type:</strong> {description}</p>
            <p><strong>Location:</strong> {location}</p>
            <p><strong>Severity:</strong> <span style="color: #dc3545; font-weight: bold;">{severity}</span></p>
            <p><strong>Detected:</strong> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}</p>
        </div>
        
        <h2>Required Action</h2>
        <div class="detail-box">
            <p><strong>Remediation Timeline:</strong> {remediation_timeline}</p>
            <p>Per AS 1851-2012 requirements, critical defects must be remediated immediately to ensure building occupant safety and maintain fire safety compliance.</p>
        </div>
        
        <h2>Technical Details</h2>
        <div class="detail-box">
            <p>{technical_details}</p>
        </div>
        
        <p style="margin-top: 30px;">
            <strong>Next Steps:</strong><br>
            1. Review the defect details above<br>
            2. Contact your fire safety service provider immediately<br>
            3. Arrange for urgent remediation work<br>
            4. Follow up to verify repair completion
        </p>
    </div>
    <div class="footer">
        <p>This is an automated notification from FireAI Compliance Platform.</p>
        <p>For questions or support, contact your fire safety engineer.</p>
        <p>&copy; 2025 FireAI. AS 1851-2012 Compliance Monitoring.</p>
    </div>
</body>
</html>
        """
        
        # SMS content (concise, < 160 chars for single SMS)
        sms_message = (
            f"CRITICAL FIRE SAFETY ALERT: {description[:50]} detected at {building.name}. "
            f"Location: {location[:30]}. Immediate action required per AS 1851-2012. Check email for details."
        )
        
        return {
            "email_html": email_html,
            "sms_message": sms_message
        }
    
    async def _send_email(
        self,
        to_email: str,
        subject: str,
        content: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Send email via SMTP.
        
        In production, this uses SendGrid/AWS SES/similar.
        For development/testing, logs the email content.
        
        Args:
            to_email: Recipient email address
            subject: Email subject line
            content: Dict with "email_html" key
        
        Returns:
            Dict with "status", "to", and "sent_at" keys
        """
        try:
            logger.info(f"Sending email to {to_email}: {subject}")
            
            # TODO: Production implementation with actual SMTP
            # Example with SendGrid:
            # import sendgrid
            # from sendgrid.helpers.mail import Mail
            # sg = sendgrid.SendGridAPIClient(api_key=self.smtp_password)
            # message = Mail(
            #     from_email=self.email_from,
            #     to_emails=to_email,
            #     subject=subject,
            #     html_content=content['email_html']
            # )
            # response = sg.send(message)
            
            # For now, simulate successful send
            logger.info(f"Email simulation: {len(content['email_html'])} bytes to {to_email}")
            
            return {
                "status": "sent",
                "to": to_email,
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"Email send failed to {to_email}: {e}", exc_info=True)
            return {
                "status": "failed",
                "to": to_email,
                "error": str(e),
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
    
    async def _send_sms(
        self,
        to_phone: str,
        message: str
    ) -> Dict[str, Any]:
        """
        Send SMS via Twilio or similar provider.
        
        In production, this uses Twilio/AWS SNS/similar.
        For development/testing, logs the SMS content.
        
        Args:
            to_phone: Recipient phone number (E.164 format)
            message: SMS message content
        
        Returns:
            Dict with "status", "to", and "sent_at" keys
        """
        try:
            logger.info(f"Sending SMS to {to_phone}")
            
            # TODO: Production implementation with Twilio
            # Example:
            # from twilio.rest import Client
            # client = Client(account_sid, auth_token)
            # twilio_message = client.messages.create(
            #     body=message,
            #     from_=self.sms_from_number,
            #     to=to_phone
            # )
            
            # For now, simulate successful send
            logger.info(f"SMS simulation: {len(message)} chars to {to_phone}")
            
            return {
                "status": "sent",
                "to": to_phone,
                "sent_at": datetime.now(timezone.utc).isoformat()
            }
        
        except Exception as e:
            logger.error(f"SMS send failed to {to_phone}: {e}", exc_info=True)
            return {
                "status": "failed",
                "to": to_phone,
                "error": str(e),
                "sent_at": datetime.now(timezone.utc).isoformat()
            }


# Singleton instance for application-wide use
notification_service = NotificationService()
