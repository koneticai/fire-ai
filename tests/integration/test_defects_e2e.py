"""
End-to-End Integration Test for Defects Workflow

This test validates the complete defects workflow from test session creation
through evidence upload, defect creation, linking, status updates, and evidence flagging.

Test Flow:
1. Create test session (inspection)
2. Upload evidence (photo)
3. Create defect (link to session)
4. Link evidence to defect
5. Get defect with linked evidence
6. Update defect status (acknowledge)
7. Get building's defects (verify it appears)
8. Flag evidence for review

This validates the complete workflow works end-to-end with a real test database.
"""

import pytest
import uuid
import json
import io
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import patch, AsyncMock

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.app.main import app
from src.app.database.core import get_db
from src.app.dependencies import get_current_active_user
from src.app.models.buildings import Building
from src.app.models.test_sessions import TestSession
from src.app.models.evidence import Evidence
from src.app.models.defects import Defect
from src.app.models.users import User
from src.app.schemas.auth import TokenPayload
from src.app.schemas.defect import DefectSeverity, DefectStatus


class TestDefectsE2E:
    """End-to-end integration tests for defects workflow."""

    @pytest.fixture(scope="class")
    def test_db_engine(self):
        """Create test database engine."""
        # Use in-memory SQLite for integration tests
        test_db_url = "sqlite+aiosqlite:///:memory:"
        engine = create_async_engine(test_db_url, echo=False)
        return engine

    @pytest.fixture(scope="class")
    async def test_db_session(self, test_db_engine):
        """Create test database session."""
        async_session = sessionmaker(
            test_db_engine, class_=AsyncSession, expire_on_commit=False
        )
        
        # Create tables
        from src.app.database.core import Base
        async with test_db_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        
        async with async_session() as session:
            yield session

    @pytest.fixture
    def test_user(self):
        """Create test user token."""
        return TokenPayload(
            username="testuser",
            user_id=uuid.uuid4(),
            jti=uuid.uuid4(),
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        )

    @pytest.fixture
    def test_building_id(self):
        """Create test building ID."""
        return uuid.uuid4()

    @pytest.fixture
    async def setup_test_data(self, test_db_session, test_user, test_building_id):
        """Set up test data: user, building."""
        # Create test user
        user = User(
            id=test_user.user_id,
            username=test_user.username,
            email="test@example.com",
            full_name_encrypted=b"Test User",
            password_hash="hashed_password",
            is_active=True,
            created_at=datetime.utcnow()
        )
        test_db_session.add(user)

        # Create test building
        building = Building(
            id=test_building_id,
            name="Test Building",
            address="123 Test Street",
            building_type="commercial",
            owner_id=test_user.user_id,
            compliance_status="active",
            created_at=datetime.utcnow()
        )
        test_db_session.add(building)

        await test_db_session.commit()
        return user, building

    @pytest.fixture
    def override_dependencies(self, test_db_session, test_user):
        """Override FastAPI dependencies for testing."""
        async def override_get_db():
            yield test_db_session

        async def override_get_current_user():
            return test_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_active_user] = override_get_current_user

        yield

        # Cleanup overrides
        app.dependency_overrides.clear()

    @pytest.fixture
    def client(self, override_dependencies):
        """Create test client with overridden dependencies."""
        return TestClient(app)

    @pytest.mark.asyncio
    async def test_complete_defects_workflow(
        self, 
        client, 
        setup_test_data, 
        test_user, 
        test_building_id
    ):
        """Test complete defects workflow end-to-end."""
        user, building = setup_test_data

        # Step 1: Create test session (inspection)
        print("Step 1: Creating test session...")
        session_data = {
            "building_id": str(test_building_id),
            "session_name": "Fire Safety Inspection - E2E Test",
            "status": "active"
        }
        
        session_response = client.post("/v1/tests/sessions/", json=session_data)
        assert session_response.status_code == 201
        
        session_result = session_response.json()
        session_id = session_result["session_id"]
        print(f"✓ Test session created: {session_id}")

        # Step 2: Upload evidence (photo)
        print("Step 2: Uploading evidence...")
        
        # Create a mock photo file
        photo_content = b"fake_photo_content_for_testing"
        photo_file = io.BytesIO(photo_content)
        
        # Mock the Go service proxy for evidence submission
        with patch('src.app.routers.evidence.get_go_service_proxy') as mock_proxy:
            mock_proxy_instance = AsyncMock()
            mock_proxy_instance.submit_evidence.return_value = {
                "evidence_id": str(uuid.uuid4()),
                "hash": "abc123def456",
                "status": "verified"
            }
            mock_proxy.return_value = mock_proxy_instance

            evidence_data = {
                "session_id": session_id,
                "evidence_type": "photo",
                "metadata": json.dumps({
                    "location": "Fire extinguisher station A1",
                    "inspector": "Test Inspector",
                    "equipment_id": "FE-001"
                })
            }
            
            files = {"file": ("test_photo.jpg", photo_file, "image/jpeg")}
            
            evidence_response = client.post(
                "/v1/evidence/submit", 
                data=evidence_data, 
                files=files
            )
            assert evidence_response.status_code == 200
            
            evidence_result = evidence_response.json()
            evidence_id = evidence_result["evidence_id"]
            print(f"✓ Evidence uploaded: {evidence_id}")

        # Step 3: Create defect (link to session)
        print("Step 3: Creating defect...")
        defect_data = {
            "test_session_id": session_id,
            "severity": "high",
            "category": "fire_extinguisher",
            "description": "Fire extinguisher pressure gauge shows 150 PSI, below minimum threshold of 180 PSI",
            "as1851_rule_code": "FE-01",
            "asset_id": str(uuid.uuid4())
        }
        
        defect_response = client.post("/v1/defects/", json=defect_data)
        assert defect_response.status_code == 201
        
        defect_result = defect_response.json()
        defect_id = defect_result["id"]
        print(f"✓ Defect created: {defect_id}")
        
        # Verify defect was created with correct data
        assert defect_result["test_session_id"] == session_id
        assert defect_result["severity"] == "high"
        assert defect_result["status"] == "open"
        assert defect_result["created_by"] == str(test_user.user_id)

        # Step 4: Link evidence to defect
        print("Step 4: Linking evidence to defect...")
        
        # First, we need to create the evidence record in the database
        # (This would normally be done by the Go service)
        from src.app.database.core import get_db
        async with get_db() as db:
            evidence_record = Evidence(
                id=uuid.UUID(evidence_id),
                session_id=uuid.UUID(session_id),
                evidence_type="photo",
                file_path=f"/evidence/{evidence_id}",
                evidence_metadata={
                    "original_filename": "test_photo.jpg",
                    "file_size": len(photo_content),
                    "uploaded_by": str(test_user.user_id),
                    "content_type": "image/jpeg",
                    "location": "Fire extinguisher station A1",
                    "inspector": "Test Inspector",
                    "equipment_id": "FE-001"
                },
                checksum="abc123def456",
                created_at=datetime.utcnow(),
                flagged_for_review=False
            )
            db.add(evidence_record)
            await db.commit()

        # Link evidence to defect
        link_data = {"defect_id": defect_id}
        link_response = client.post(
            f"/v1/evidence/{evidence_id}/link-defect", 
            json=link_data
        )
        assert link_response.status_code == 200
        
        link_result = link_response.json()
        print(f"✓ Evidence linked to defect: {link_result['message']}")

        # Step 5: Get defect with linked evidence
        print("Step 5: Retrieving defect with evidence...")
        defect_get_response = client.get(f"/v1/defects/{defect_id}")
        assert defect_get_response.status_code == 200
        
        defect_with_evidence = defect_get_response.json()
        assert defect_with_evidence["id"] == defect_id
        assert evidence_id in defect_with_evidence["evidence_ids"]
        print(f"✓ Defect retrieved with {len(defect_with_evidence['evidence_ids'])} evidence items")

        # Step 6: Update defect status (acknowledge)
        print("Step 6: Updating defect status to acknowledged...")
        update_data = {"status": "acknowledged"}
        
        update_response = client.patch(
            f"/v1/defects/{defect_id}", 
            json=update_data
        )
        assert update_response.status_code == 200
        
        updated_defect = update_response.json()
        assert updated_defect["status"] == "acknowledged"
        assert updated_defect["acknowledged_by"] == str(test_user.user_id)
        assert updated_defect["acknowledged_at"] is not None
        print(f"✓ Defect status updated to: {updated_defect['status']}")

        # Step 7: Get building's defects (verify it appears)
        print("Step 7: Retrieving building's defects...")
        building_defects_response = client.get(
            f"/v1/defects/buildings/{test_building_id}/defects"
        )
        assert building_defects_response.status_code == 200
        
        building_defects = building_defects_response.json()
        assert len(building_defects) == 1
        assert building_defects[0]["id"] == defect_id
        assert building_defects[0]["building_id"] == str(test_building_id)
        print(f"✓ Building has {len(building_defects)} defect(s)")

        # Step 8: Flag evidence for review
        print("Step 8: Flagging evidence for review...")
        
        # Create admin user for flagging
        admin_user = TokenPayload(
            username="admin_user_admin",
            user_id=uuid.uuid4(),
            jti=uuid.uuid4(),
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        )
        
        # Override the current user to be admin for this request
        async def override_admin_user():
            return admin_user
        
        app.dependency_overrides[get_current_active_user] = override_admin_user

        flag_data = {"flag_reason": "Suspicious content detected during E2E test"}
        flag_response = client.patch(
            f"/v1/evidence/{evidence_id}/flag", 
            json=flag_data
        )
        assert flag_response.status_code == 200
        
        flag_result = flag_response.json()
        assert flag_result["flagged_for_review"] == True
        assert flag_result["flag_reason"] == "Suspicious content detected during E2E test"
        assert flag_result["flagged_by"] == str(admin_user.user_id)
        print(f"✓ Evidence flagged for review: {flag_result['flag_reason']}")

        # Verify the evidence is now flagged in the database
        evidence_get_response = client.get(f"/v1/evidence/{evidence_id}")
        assert evidence_get_response.status_code == 200
        
        evidence_metadata = evidence_get_response.json()
        assert evidence_metadata["flagged_for_review"] == True
        print(f"✓ Evidence flagging verified in database")

        # Final verification: Get test session defects
        print("Final verification: Getting test session defects...")
        session_defects_response = client.get(
            f"/v1/defects/test-sessions/{session_id}/defects"
        )
        assert session_defects_response.status_code == 200
        
        session_defects = session_defects_response.json()
        assert len(session_defects) == 1
        assert session_defects[0]["id"] == defect_id
        assert session_defects[0]["test_session_id"] == session_id
        print(f"✓ Test session has {len(session_defects)} defect(s)")

        print("\n🎉 Complete defects workflow test PASSED!")
        print("All 8 steps completed successfully:")
        print("1. ✓ Test session created")
        print("2. ✓ Evidence uploaded")
        print("3. ✓ Defect created")
        print("4. ✓ Evidence linked to defect")
        print("5. ✓ Defect retrieved with evidence")
        print("6. ✓ Defect status updated")
        print("7. ✓ Building defects retrieved")
        print("8. ✓ Evidence flagged for review")

    @pytest.mark.asyncio
    async def test_defects_workflow_error_scenarios(
        self, 
        client, 
        setup_test_data, 
        test_user, 
        test_building_id
    ):
        """Test error scenarios in the defects workflow."""
        user, building = setup_test_data

        # Test 1: Create defect without valid test session
        print("Testing error scenario: Invalid test session...")
        invalid_session_id = str(uuid.uuid4())
        defect_data = {
            "test_session_id": invalid_session_id,
            "severity": "high",
            "category": "fire_extinguisher",
            "description": "Test defect with invalid session"
        }
        
        defect_response = client.post("/v1/defects/", json=defect_data)
        assert defect_response.status_code == 404
        assert "Test session not found" in defect_response.json()["detail"]
        print("✓ Invalid test session properly rejected")

        # Test 2: Create defect with invalid severity
        print("Testing error scenario: Invalid severity...")
        # First create a valid test session
        session_data = {
            "building_id": str(test_building_id),
            "session_name": "Error Test Session",
            "status": "active"
        }
        session_response = client.post("/v1/tests/sessions/", json=session_data)
        session_id = session_response.json()["session_id"]

        invalid_defect_data = {
            "test_session_id": session_id,
            "severity": "invalid_severity",
            "category": "fire_extinguisher",
            "description": "Test defect with invalid severity"
        }
        
        defect_response = client.post("/v1/defects/", json=invalid_defect_data)
        assert defect_response.status_code == 400
        assert "Invalid severity" in defect_response.json()["detail"]
        print("✓ Invalid severity properly rejected")

        # Test 3: Update defect with invalid status transition
        print("Testing error scenario: Invalid status transition...")
        # Create a valid defect first
        valid_defect_data = {
            "test_session_id": session_id,
            "severity": "high",
            "category": "fire_extinguisher",
            "description": "Test defect for status transition"
        }
        defect_response = client.post("/v1/defects/", json=valid_defect_data)
        defect_id = defect_response.json()["id"]

        # Try to transition directly from open to closed (invalid)
        invalid_update_data = {"status": "closed"}
        update_response = client.patch(
            f"/v1/defects/{defect_id}", 
            json=invalid_update_data
        )
        assert update_response.status_code == 422
        assert "Invalid status transition" in update_response.json()["detail"]
        print("✓ Invalid status transition properly rejected")

        # Test 4: Access defect from different user's building
        print("Testing error scenario: Unauthorized access...")
        # Create another user
        other_user_id = uuid.uuid4()
        other_user = TokenPayload(
            username="otheruser",
            user_id=other_user_id,
            jti=uuid.uuid4(),
            exp=int((datetime.utcnow() + timedelta(hours=1)).timestamp())
        )
        
        # Override current user
        async def override_other_user():
            return other_user
        
        app.dependency_overrides[get_current_active_user] = override_other_user

        # Try to access the defect
        defect_get_response = client.get(f"/v1/defects/{defect_id}")
        assert defect_get_response.status_code == 404
        assert "Defect not found" in defect_get_response.json()["detail"]
        print("✓ Unauthorized access properly rejected")

        print("\n🎉 Error scenario tests PASSED!")
        print("All error scenarios properly handled:")
        print("1. ✓ Invalid test session rejected")
        print("2. ✓ Invalid severity rejected")
        print("3. ✓ Invalid status transition rejected")
        print("4. ✓ Unauthorized access rejected")

    @pytest.mark.asyncio
    async def test_defects_workflow_performance(
        self, 
        client, 
        setup_test_data, 
        test_user, 
        test_building_id
    ):
        """Test performance aspects of the defects workflow."""
        user, building = setup_test_data

        # Create multiple test sessions and defects for performance testing
        print("Testing performance: Creating multiple defects...")
        
        session_ids = []
        defect_ids = []
        
        start_time = datetime.utcnow()
        
        for i in range(5):  # Create 5 test sessions with defects
            # Create test session
            session_data = {
                "building_id": str(test_building_id),
                "session_name": f"Performance Test Session {i+1}",
                "status": "active"
            }
            session_response = client.post("/v1/tests/sessions/", json=session_data)
            session_id = session_response.json()["session_id"]
            session_ids.append(session_id)
            
            # Create defect for this session
            defect_data = {
                "test_session_id": session_id,
                "severity": ["critical", "high", "medium", "low"][i % 4],
                "category": ["fire_extinguisher", "alarm_system", "hose_reel", "emergency_lighting"][i % 4],
                "description": f"Performance test defect {i+1}"
            }
            defect_response = client.post("/v1/defects/", json=defect_data)
            defect_id = defect_response.json()["id"]
            defect_ids.append(defect_id)
        
        creation_time = datetime.utcnow() - start_time
        print(f"✓ Created 5 defects in {creation_time.total_seconds():.2f} seconds")

        # Test listing performance
        print("Testing performance: Listing defects...")
        start_time = datetime.utcnow()
        
        list_response = client.get("/v1/defects/?page=1&page_size=10")
        assert list_response.status_code == 200
        
        list_time = datetime.utcnow() - start_time
        defects_list = list_response.json()
        print(f"✓ Listed {len(defects_list['defects'])} defects in {list_time.total_seconds():.3f} seconds")
        
        # Test filtering performance
        print("Testing performance: Filtering defects by severity...")
        start_time = datetime.utcnow()
        
        filter_response = client.get("/v1/defects/?severity=high&severity=critical")
        assert filter_response.status_code == 200
        
        filter_time = datetime.utcnow() - start_time
        filtered_defects = filter_response.json()
        print(f"✓ Filtered defects in {filter_time.total_seconds():.3f} seconds")

        # Test building defects performance
        print("Testing performance: Getting building defects...")
        start_time = datetime.utcnow()
        
        building_defects_response = client.get(
            f"/v1/defects/buildings/{test_building_id}/defects"
        )
        assert building_defects_response.status_code == 200
        
        building_defects_time = datetime.utcnow() - start_time
        building_defects = building_defects_response.json()
        print(f"✓ Retrieved {len(building_defects)} building defects in {building_defects_time.total_seconds():.3f} seconds")

        # Performance assertions
        assert creation_time.total_seconds() < 5.0, "Defect creation took too long"
        assert list_time.total_seconds() < 1.0, "Defect listing took too long"
        assert filter_time.total_seconds() < 1.0, "Defect filtering took too long"
        assert building_defects_time.total_seconds() < 1.0, "Building defects retrieval took too long"

        print("\n🎉 Performance tests PASSED!")
        print("All performance benchmarks met:")
        print(f"1. ✓ Defect creation: {creation_time.total_seconds():.2f}s (< 5.0s)")
        print(f"2. ✓ Defect listing: {list_time.total_seconds():.3f}s (< 1.0s)")
        print(f"3. ✓ Defect filtering: {filter_time.total_seconds():.3f}s (< 1.0s)")
        print(f"4. ✓ Building defects: {building_defects_time.total_seconds():.3f}s (< 1.0s)")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
