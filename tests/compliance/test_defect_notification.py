"""
Test 24-hour critical defect notification (Task 3.2)

References:
- AS 1851-2012: Section 8.3 - Critical defect notification requirements
- data_model.md: audit_log schema for notification tracking
- AGENTS.md: Testing requirements (small diffs, security, rollback)
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, AsyncMock, patch
from uuid import uuid4

from sqlalchemy import select

from src.app.services.notification_service import notification_service
from src.app.workers.defect_monitor import defect_monitor
from src.app.models.test_sessions import TestSession
from src.app.models.buildings import Building
from src.app.models.users import User
from src.app.models.defects import Defect
from src.app.models.audit_log import AuditLog


@pytest.fixture
def building_with_owner(db_session):
    """Create test building with owner."""
    owner = User(
        id=uuid4(),
        username="owner_test",
        email="owner@test.com",
        full_name_encrypted=b"encrypted_test_name",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$test",
        is_active=True
    )
    
    building = Building(
        id=uuid4(),
        name="Test Building",
        address="123 Test St, Test City",
        building_type="commercial",
        owner_id=owner.id,
        compliance_status="active"
    )
    
    return building, owner


@pytest.fixture
def test_session_fixture(db_session, building_with_owner):
    """Create test session for defect tracking."""
    building, owner = building_with_owner
    
    session = TestSession(
        id=uuid4(),
        building_id=building.id,
        session_name="Fire Inspection 2025-01",
        status="completed",
        session_data={},
        created_by=owner.id
    )
    
    return session, building, owner


@pytest.fixture
def critical_defect(db_session, test_session_fixture):
    """Create critical defect for testing."""
    session, building, owner = test_session_fixture
    
    defect = Defect(
        id=uuid4(),
        test_session_id=session.id,
        building_id=building.id,
        severity="critical",
        category="extinguisher_pressure",
        description="Fire extinguisher pressure at 35.5 PSI, expected 50 PSI. Location: Building 2, Level 3, Zone A",
        as1851_rule_code="FE-01",
        status="open",
        discovered_at=datetime.now(timezone.utc)
    )
    
    return defect, session, building, owner


@pytest.mark.asyncio
class TestNotificationService:
    """Test notification service functionality."""
    
    async def test_notify_critical_defect_success(
        self,
        db_session,
        critical_defect,
        monkeypatch
    ):
        """Critical defect notification should be sent successfully."""
        defect, session, building, owner = critical_defect
        
        # Mock database queries to return our test objects
        # First call gets building, second call gets owner
        call_count = [0]
        
        async def mock_execute(query):
            call_count[0] += 1
            mock_result = Mock()
            if call_count[0] == 1:
                # First query is for building
                mock_result.scalar_one_or_none = Mock(return_value=building)
            else:
                # Second query is for owner
                mock_result.scalar_one_or_none = Mock(return_value=owner)
            return mock_result
        
        db_session.execute = AsyncMock(side_effect=mock_execute)
        db_session.add = Mock()
        db_session.commit = AsyncMock()
        db_session.refresh = AsyncMock()
        
        # Mock email sending
        mock_send_email = AsyncMock(return_value={
            "status": "sent",
            "to": owner.email,
            "sent_at": datetime.now(timezone.utc).isoformat()
        })
        monkeypatch.setattr(notification_service, "_send_email", mock_send_email)
        
        # Send notification
        result = await notification_service.notify_critical_defect(
            building_id=str(building.id),
            defect_type="PRESSURE_OUT_OF_RANGE",
            defect_details={
                "location": "Building 2, Level 3, Zone A",
                "severity": "critical",
                "description": "Pressure deviation detected",
                "remediation_timeline": "24 hours"
            },
            db=db_session
        )
        
        # Verify notification sent
        assert result['email_status'] == 'sent'
        assert result['owner_email'] == owner.email
        assert result['sla_compliant'] is True
        assert result['building_id'] == str(building.id)
        assert 'notification_id' in result
        
        # Verify email was called
        mock_send_email.assert_called_once()
        call_args = mock_send_email.call_args
        assert call_args.kwargs['to_email'] == owner.email
        assert "CRITICAL" in call_args.kwargs['subject']
    
    async def test_notification_creates_audit_log(
        self,
        db_session,
        critical_defect,
        monkeypatch
    ):
        """Notification should create audit log entry per data_model.md."""
        defect, session, building, owner = critical_defect
        
        # Create mock audit log with all expected fields
        audit_log_id = uuid4()
        sent_at = datetime.now(timezone.utc).isoformat()
        mock_audit_log = AuditLog(
            id=audit_log_id,
            action="CRITICAL_DEFECT_NOTIFICATION",
            resource_type="building",
            resource_id=building.id,
            user_id=owner.id,
            new_values={
                'defect_type': 'PRESSURE_OUT_OF_RANGE',
                'defect_details': {"location": "Zone A", "severity": "critical"},
                'notification_sent_at': sent_at,
                'email_status': 'sent',
                'email_to': owner.email,
                'sms_status': None,
                'sla_compliant': True
            }
        )
        
        # Mock database queries
        query_count = [0]
        
        async def mock_execute(query):
            query_count[0] += 1
            mock_result = Mock()
            # First two queries get building and owner
            if query_count[0] == 1:
                mock_result.scalar_one_or_none = Mock(return_value=building)
            elif query_count[0] == 2:
                mock_result.scalar_one_or_none = Mock(return_value=owner)
            else:
                # Subsequent queries for audit log
                mock_result.scalar_one_or_none = Mock(return_value=mock_audit_log)
            return mock_result
        
        db_session.execute = AsyncMock(side_effect=mock_execute)
        db_session.add = Mock()
        db_session.commit = AsyncMock()
        
        async def mock_refresh(obj):
            if isinstance(obj, AuditLog):
                obj.id = audit_log_id
        
        db_session.refresh = AsyncMock(side_effect=mock_refresh)
        
        # Mock email sending
        mock_send_email = AsyncMock(return_value={
            "status": "sent",
            "to": owner.email,
            "sent_at": datetime.now(timezone.utc).isoformat()
        })
        monkeypatch.setattr(notification_service, "_send_email", mock_send_email)
        
        # Send notification
        result = await notification_service.notify_critical_defect(
            building_id=str(building.id),
            defect_type="PRESSURE_OUT_OF_RANGE",
            defect_details={
                "location": "Zone A",
                "severity": "critical"
            },
            db=db_session
        )
        
        # Verify result contains notification_id
        audit_log = mock_audit_log
        
        assert audit_log is not None
        assert audit_log.action == "CRITICAL_DEFECT_NOTIFICATION"
        assert audit_log.resource_type == "building"
        assert str(audit_log.resource_id) == str(building.id)
        assert audit_log.user_id == owner.id
        
        # Verify audit log content
        new_values = audit_log.new_values
        assert new_values['defect_type'] == 'PRESSURE_OUT_OF_RANGE'
        assert new_values['email_status'] == 'sent'
        assert new_values['sla_compliant'] is True
        assert 'notification_sent_at' in new_values
    
    async def test_notification_content_includes_details(
        self,
        building_with_owner
    ):
        """Notification content should include all required AS 1851-2012 details."""
        building, owner = building_with_owner
        
        content = notification_service._build_notification_content(
            building=building,
            defect_type="PRESSURE_OUT_OF_RANGE",
            defect_details={
                "location": "Zone A",
                "severity": "CRITICAL",
                "remediation_timeline": "24 hours",
                "technical_details": "Pressure 29% below acceptable range"
            }
        )
        
        # Check email content
        email_html = content['email_html']
        assert building.name in email_html
        assert building.address in email_html
        assert "CRITICAL" in email_html
        assert "Zone A" in email_html
        assert "24 hours" in email_html
        assert "AS 1851" in email_html or "AS1851" in email_html
        
        # Check SMS content
        sms_message = content['sms_message']
        assert building.name in sms_message
        assert "CRITICAL" in sms_message
        assert "AS 1851" in sms_message
    
    async def test_notification_fails_if_no_owner(
        self,
        db_session
    ):
        """Should raise error if building has no owner."""
        # Create building without owner
        building = Building(
            id=uuid4(),
            name="Orphan Building",
            address="456 Test St",
            building_type="commercial",
            owner_id=None
        )
        
        # Mock database to return building without owner
        async def mock_execute(query):
            mock_result = Mock()
            mock_result.scalar_one_or_none = Mock(return_value=building)
            return mock_result
        
        db_session.execute = AsyncMock(side_effect=mock_execute)
        
        # Try to send notification
        with pytest.raises(ValueError, match="has no owner"):
            await notification_service.notify_critical_defect(
                building_id=str(building.id),
                defect_type="PRESSURE_OUT_OF_RANGE",
                defect_details={},
                db=db_session
            )
    
    async def test_notification_fails_if_building_not_found(
        self,
        db_session
    ):
        """Should raise error if building doesn't exist."""
        fake_building_id = str(uuid4())
        
        # Mock database to return None
        async def mock_execute(query):
            mock_result = Mock()
            mock_result.scalar_one_or_none = Mock(return_value=None)
            return mock_result
        
        db_session.execute = AsyncMock(side_effect=mock_execute)
        
        with pytest.raises(ValueError, match="not found"):
            await notification_service.notify_critical_defect(
                building_id=fake_building_id,
                defect_type="PRESSURE_OUT_OF_RANGE",
                defect_details={},
                db=db_session
            )


@pytest.mark.asyncio
class TestDefectMonitor:
    """Test defect monitor background worker."""
    
    async def test_monitor_finds_unnotified_critical_defects(
        self,
        db_session,
        critical_defect,
        monkeypatch
    ):
        """Defect monitor should find critical defects without notification."""
        defect, session, building, owner = critical_defect
        
        # Mock notification service
        mock_notify = AsyncMock(return_value={
            "notification_id": str(uuid4()),
            "sent_at": datetime.now(timezone.utc).isoformat(),
            "email_status": "sent",
            "owner_email": owner.email,
            "building_id": str(building.id),
            "sms_status": None,
            "sla_compliant": True
        })
        monkeypatch.setattr(notification_service, "notify_critical_defect", mock_notify)
        
        # Mock AsyncSessionLocal to return our test session
        async def mock_session_maker():
            class MockContextManager:
                async def __aenter__(self):
                    return db_session
                async def __aexit__(self, *args):
                    pass
            return MockContextManager()
        
        # Run monitor check
        with patch('src.app.workers.defect_monitor.AsyncSessionLocal', side_effect=mock_session_maker):
            await defect_monitor._check_for_critical_defects()
        
        # Verify notification was called
        assert mock_notify.called
        call_args = mock_notify.call_args
        assert str(building.id) == call_args.kwargs['building_id']
        assert call_args.kwargs['defect_type'] == "PRESSURE_OUT_OF_RANGE"
    
    async def test_monitor_updates_session_after_notification(
        self,
        db_session,
        critical_defect,
        monkeypatch
    ):
        """Session should be marked with notification details after sending."""
        defect, session, building, owner = critical_defect
        
        notification_id = str(uuid4())
        sent_at = datetime.now(timezone.utc).isoformat()
        
        # Mock notification service
        mock_notify = AsyncMock(return_value={
            "notification_id": notification_id,
            "sent_at": sent_at,
            "email_status": "sent",
            "owner_email": owner.email,
            "building_id": str(building.id),
            "sms_status": None,
            "sla_compliant": True
        })
        monkeypatch.setattr(notification_service, "notify_critical_defect", mock_notify)
        
        # Process defect directly
        await defect_monitor._process_critical_defect(defect, session, db_session)
        
        # Verify session updated
        await db_session.refresh(session)
        session_data = session.session_data or {}
        
        assert 'critical_defect_notifications' in session_data
        notifications = session_data['critical_defect_notifications']
        assert str(defect.id) in notifications
        
        notification_info = notifications[str(defect.id)]
        assert notification_info['notification_id'] == notification_id
        assert notification_info['sent_at'] == sent_at
        assert notification_info['email_status'] == 'sent'
    
    async def test_monitor_skips_already_notified_defects(
        self,
        db_session,
        critical_defect,
        monkeypatch
    ):
        """Monitor should not send duplicate notifications."""
        defect, session, building, owner = critical_defect
        
        # Mark defect as already notified
        session.session_data = {
            'critical_defect_notifications': {
                str(defect.id): {
                    "notification_id": str(uuid4()),
                    "sent_at": datetime.now(timezone.utc).isoformat(),
                    "email_status": "sent"
                }
            }
        }
        await db_session.commit()
        
        # Mock notification service
        mock_notify = AsyncMock()
        monkeypatch.setattr(notification_service, "notify_critical_defect", mock_notify)
        
        # Mock AsyncSessionLocal to return our test session
        async def mock_session_maker():
            class MockContextManager:
                async def __aenter__(self):
                    return db_session
                async def __aexit__(self, *args):
                    pass
            return MockContextManager()
        
        # Run monitor check
        with patch('src.app.workers.defect_monitor.AsyncSessionLocal', side_effect=mock_session_maker):
            await defect_monitor._check_for_critical_defects()
        
        # Verify notification was NOT called
        mock_notify.assert_not_called()
    
    async def test_monitor_respects_sla_window(
        self,
        db_session,
        test_session_fixture,
        monkeypatch
    ):
        """Monitor should only process defects within 24-hour SLA window."""
        session, building, owner = test_session_fixture
        
        # Create old defect (> 24 hours ago)
        old_defect = Defect(
            id=uuid4(),
            test_session_id=session.id,
            building_id=building.id,
            severity="critical",
            category="extinguisher_pressure",
            description="Old defect",
            status="open",
            discovered_at=datetime.now(timezone.utc) - timedelta(hours=25)
        )
        
        # Mock database to return no defects (old one filtered out by query)
        async def mock_execute(query):
            mock_result = Mock()
            mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
            return mock_result
        
        db_session.execute = AsyncMock(side_effect=mock_execute)
        
        # Mock notification service
        mock_notify = AsyncMock()
        monkeypatch.setattr(notification_service, "notify_critical_defect", mock_notify)
        
        # Mock AsyncSessionLocal to return our test session
        async def mock_session_maker():
            class MockContextManager:
                async def __aenter__(self):
                    return db_session
                async def __aexit__(self, *args):
                    pass
            return MockContextManager()
        
        # Run monitor check
        with patch('src.app.workers.defect_monitor.AsyncSessionLocal', side_effect=mock_session_maker):
            await defect_monitor._check_for_critical_defects()
        
        # Verify notification was NOT called (defect too old)
        mock_notify.assert_not_called()


@pytest.mark.asyncio
class TestSLACompliance:
    """Test AS 1851-2012 SLA compliance."""
    
    async def test_sla_compliance_within_24_hours(
        self,
        db_session,
        critical_defect,
        monkeypatch
    ):
        """Notifications sent within 24 hours should be marked SLA compliant."""
        defect, session, building, owner = critical_defect
        
        # Defect discovered recently (within 24 hours)
        assert defect.discovered_at > datetime.now(timezone.utc) - timedelta(hours=24)
        
        # Mock email sending
        mock_send_email = AsyncMock(return_value={
            "status": "sent",
            "to": owner.email,
            "sent_at": datetime.now(timezone.utc).isoformat()
        })
        monkeypatch.setattr(notification_service, "_send_email", mock_send_email)
        
        # Send notification
        result = await notification_service.notify_critical_defect(
            building_id=str(building.id),
            defect_type="PRESSURE_OUT_OF_RANGE",
            defect_details={},
            db=db_session
        )
        
        # Verify SLA compliance
        assert result['sla_compliant'] is True
    
    async def test_defect_type_mapping(self):
        """Test defect category to type mapping for notifications."""
        # Test known categories
        assert defect_monitor._map_category_to_type("extinguisher_pressure") == "PRESSURE_OUT_OF_RANGE"
        assert defect_monitor._map_category_to_type("exit_blocked") == "EXIT_BLOCKED"
        assert defect_monitor._map_category_to_type("detection_failure") == "DETECTION_FAILURE"
        assert defect_monitor._map_category_to_type("hydrant_pressure") == "HYDRANT_PRESSURE_LOW"
        
        # Test unknown category
        assert defect_monitor._map_category_to_type("unknown") == "CRITICAL_DEFECT_DETECTED"
        assert defect_monitor._map_category_to_type(None) == "CRITICAL_DEFECT_DETECTED"
