#!/usr/bin/env python3
"""
Demo Data Seeding Script for FireAI Compliance Platform

Creates realistic test data for three buildings with different compliance profiles:
- Building A: Perfect Compliance (95% score)
- Building B: Good Compliance (62% score)  
- Building C: Poor Compliance (45% score)

This script is idempotent - can be run multiple times without creating duplicates.
"""

import os
import sys
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import Optional

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..', 'src'))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Import models
from app.models.buildings import Building
from app.models.test_sessions import TestSession
from app.models.evidence import Evidence
from app.models.defects import Defect
from app.models.users import User


def get_sync_database_url() -> str:
    """Get synchronous database URL from environment"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    # Convert async URL to sync URL if needed
    if "postgresql+asyncpg://" in database_url:
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql://")
    
    return database_url


def create_demo_user(session) -> User:
    """Create or get demo user for testing"""
    # Check if demo user already exists
    demo_user = session.query(User).filter(User.username == "demo_user").first()
    
    if not demo_user:
        # Create demo user
        demo_user = User(
            id=uuid.uuid4(),
            username="demo_user",
            email="demo@fireai.com",
            full_name_encrypted=b"Demo User (encrypted)",
            password_hash="$2b$12$dummy_hash_for_demo_purposes_only",
            is_active=True,
            created_at=datetime.utcnow()
        )
        session.add(demo_user)
        session.commit()
        session.refresh(demo_user)
        print(f"✅ Created demo user: {demo_user.username}")
    else:
        print(f"✅ Using existing demo user: {demo_user.username}")
    
    return demo_user


def create_building_a_perfect_compliance(session, user: User) -> Building:
    """Create Building A - Perfect Compliance (Target Score 95%)"""
    # Check if building already exists
    building = session.query(Building).filter(Building.name == "Sydney Office Tower").first()
    
    if not building:
        building = Building(
            id=uuid.uuid4(),
            name="Sydney Office Tower",
            address="123 George Street, Sydney NSW 2000",
            building_type="Office",
            owner_id=user.id,
            compliance_status="compliant",
            created_at=datetime.utcnow() - timedelta(days=365)
        )
        session.add(building)
        session.commit()
        session.refresh(building)
        print(f"✅ Created Building A: {building.name}")
    else:
        print(f"✅ Using existing Building A: {building.name}")
    
    # Create 20 test sessions over last 12 months (all passed)
    test_sessions = session.query(TestSession).filter(TestSession.building_id == building.id).all()
    
    if len(test_sessions) < 20:
        base_date = datetime.utcnow() - timedelta(days=365)
        
        for i in range(20):
            session_date = base_date + timedelta(days=i * 18)  # Spread over 12 months
            
            test_session = TestSession(
                id=uuid.uuid4(),
                building_id=building.id,
                session_name=f"Monthly AS1851 Inspection - {session_date.strftime('%B %Y')}",
                status="completed",
                session_data={
                    "test_results": {
                        "fire_extinguishers": "passed",
                        "hose_reels": "passed", 
                        "emergency_lights": "passed",
                        "smoke_detectors": "passed",
                        "sprinkler_system": "passed"
                    },
                    "inspector": "John Smith",
                    "compliance_score": 95
                },
                created_by=user.id,
                created_at=session_date
            )
            session.add(test_session)
        
        session.commit()
        print(f"✅ Created 20 test sessions for Building A")
    
    # Create 50 evidence items (all with valid WORM hash + device attestation)
    test_sessions = session.query(TestSession).filter(TestSession.building_id == building.id).all()
    evidence_count = session.query(Evidence).join(TestSession).filter(TestSession.building_id == building.id).count()
    
    if evidence_count < 50:
        evidence_types = [
            "fire_extinguisher_photo", "hose_reel_inspection", "emergency_light_test",
            "smoke_detector_check", "sprinkler_head_photo", "exit_sign_verification",
            "fire_door_inspection", "alarm_panel_test", "evacuation_route_photo",
            "fire_blanket_check"
        ]
        
        for i in range(50):
            session_obj = test_sessions[i % len(test_sessions)]
            evidence_type = evidence_types[i % len(evidence_types)]
            
            # Generate realistic WORM hash
            content = f"demo_evidence_{i}_{evidence_type}_{session_obj.id}"
            worm_hash = hashlib.sha256(content.encode()).hexdigest()
            
            evidence = Evidence(
                id=uuid.uuid4(),
                session_id=session_obj.id,
                evidence_type=evidence_type,
                file_path=f"/evidence/{session_obj.id}/{evidence_type}_{i:02d}.jpg",
                evidence_metadata={
                    "device_attestation": True,
                    "worm_hash": worm_hash,
                    "file_size": 1024 * 512,  # 512KB
                    "camera_model": "iPhone 14 Pro",
                    "gps_coordinates": {"lat": -33.8688, "lng": 151.2093},
                    "timestamp": session_obj.created_at.isoformat()
                },
                checksum=worm_hash,
                created_at=session_obj.created_at
            )
            session.add(evidence)
        
        session.commit()
        print(f"✅ Created 50 evidence items for Building A")
    
    # No defects for perfect compliance
    defect_count = session.query(Defect).filter(Defect.building_id == building.id).count()
    if defect_count == 0:
        print(f"✅ Building A has 0 defects (perfect compliance)")
    
    return building


def create_building_b_good_compliance(session, user: User) -> Building:
    """Create Building B - Good Compliance (Target Score 62%)"""
    # Check if building already exists
    building = session.query(Building).filter(Building.name == "Melbourne Retail Complex").first()
    
    if not building:
        building = Building(
            id=uuid.uuid4(),
            name="Melbourne Retail Complex",
            address="456 Collins Street, Melbourne VIC 3000",
            building_type="Retail",
            owner_id=user.id,
            compliance_status="pending_review",
            created_at=datetime.utcnow() - timedelta(days=300)
        )
        session.add(building)
        session.commit()
        session.refresh(building)
        print(f"✅ Created Building B: {building.name}")
    else:
        print(f"✅ Using existing Building B: {building.name}")
    
    # Create 15 test sessions (3 overdue tests)
    test_sessions = session.query(TestSession).filter(TestSession.building_id == building.id).all()
    
    if len(test_sessions) < 15:
        base_date = datetime.utcnow() - timedelta(days=300)
        
        for i in range(15):
            session_date = base_date + timedelta(days=i * 20)
            is_overdue = i in [12, 13, 14]  # Last 3 sessions are overdue
            
            test_session = TestSession(
                id=uuid.uuid4(),
                building_id=building.id,
                session_name=f"Quarterly Safety Inspection - {session_date.strftime('%B %Y')}",
                status="completed" if not is_overdue else "overdue",
                session_data={
                    "test_results": {
                        "fire_extinguishers": "passed" if not is_overdue else "pending",
                        "hose_reels": "passed",
                        "emergency_lights": "passed" if not is_overdue else "pending",
                        "smoke_detectors": "passed",
                        "sprinkler_system": "passed"
                    },
                    "inspector": "Sarah Johnson",
                    "compliance_score": 62 if not is_overdue else 45,
                    "overdue": is_overdue
                },
                created_by=user.id,
                created_at=session_date
            )
            session.add(test_session)
        
        session.commit()
        print(f"✅ Created 15 test sessions for Building B (3 overdue)")
    
    # Create 30 evidence items (2 missing device attestation)
    test_sessions = session.query(TestSession).filter(TestSession.building_id == building.id).all()
    evidence_count = session.query(Evidence).join(TestSession).filter(TestSession.building_id == building.id).count()
    
    if evidence_count < 30:
        evidence_types = [
            "fire_extinguisher_photo", "hose_reel_inspection", "emergency_light_test",
            "smoke_detector_check", "sprinkler_head_photo", "exit_sign_verification"
        ]
        
        for i in range(30):
            session_obj = test_sessions[i % len(test_sessions)]
            evidence_type = evidence_types[i % len(evidence_types)]
            missing_attestation = i in [28, 29]  # Last 2 items missing attestation
            
            content = f"demo_evidence_b_{i}_{evidence_type}_{session_obj.id}"
            worm_hash = hashlib.sha256(content.encode()).hexdigest()
            
            evidence = Evidence(
                id=uuid.uuid4(),
                session_id=session_obj.id,
                evidence_type=evidence_type,
                file_path=f"/evidence/{session_obj.id}/{evidence_type}_{i:02d}.jpg",
                evidence_metadata={
                    "device_attestation": not missing_attestation,
                    "worm_hash": worm_hash,
                    "file_size": 1024 * 256,  # 256KB
                    "camera_model": "Samsung Galaxy S22",
                    "gps_coordinates": {"lat": -37.8136, "lng": 144.9631},
                    "timestamp": session_obj.created_at.isoformat(),
                    "attestation_missing": missing_attestation
                },
                checksum=worm_hash,
                created_at=session_obj.created_at
            )
            session.add(evidence)
        
        session.commit()
        print(f"✅ Created 30 evidence items for Building B (2 missing attestation)")
    
    # Create 3 medium defects (status: acknowledged, not repaired)
    test_sessions = session.query(TestSession).filter(TestSession.building_id == building.id).all()
    defect_count = session.query(Defect).filter(Defect.building_id == building.id).count()
    
    if defect_count < 3:
        defect_descriptions = [
            "Fire extinguisher pressure gauge reading below recommended level",
            "Hose reel connection showing minor leak during pressure test",
            "Emergency exit light flickering intermittently"
        ]
        
        for i in range(3):
            session_obj = test_sessions[i % len(test_sessions)]
            discovered_date = session_obj.created_at - timedelta(days=10 + i * 5)
            acknowledged_date = discovered_date + timedelta(days=2)
            
            defect = Defect(
                id=uuid.uuid4(),
                test_session_id=session_obj.id,
                building_id=building.id,
                severity="medium",
                category="equipment_maintenance",
                description=defect_descriptions[i],
                as1851_rule_code=f"FE-{i+1:02d}",
                status="acknowledged",
                discovered_at=discovered_date,
                acknowledged_at=acknowledged_date,
                created_by=user.id,
                acknowledged_by=user.id,
                created_at=discovered_date
            )
            session.add(defect)
        
        session.commit()
        print(f"✅ Created 3 medium defects for Building B (acknowledged, not repaired)")
    
    return building


def create_building_c_poor_compliance(session, user: User) -> Building:
    """Create Building C - Poor Compliance (Target Score 45%)"""
    # Check if building already exists
    building = session.query(Building).filter(Building.name == "Brisbane Warehouse").first()
    
    if not building:
        building = Building(
            id=uuid.uuid4(),
            name="Brisbane Warehouse",
            address="789 Eagle Street, Brisbane QLD 4000",
            building_type="Warehouse",
            owner_id=user.id,
            compliance_status="non_compliant",
            created_at=datetime.utcnow() - timedelta(days=200)
        )
        session.add(building)
        session.commit()
        session.refresh(building)
        print(f"✅ Created Building C: {building.name}")
    else:
        print(f"✅ Using existing Building C: {building.name}")
    
    # Create 10 test sessions (5 overdue tests)
    test_sessions = session.query(TestSession).filter(TestSession.building_id == building.id).all()
    
    if len(test_sessions) < 10:
        base_date = datetime.utcnow() - timedelta(days=200)
        
        for i in range(10):
            session_date = base_date + timedelta(days=i * 20)
            is_overdue = i >= 5  # Last 5 sessions are overdue
            
            test_session = TestSession(
                id=uuid.uuid4(),
                building_id=building.id,
                session_name=f"Safety Inspection - {session_date.strftime('%B %Y')}",
                status="completed" if not is_overdue else "overdue",
                session_data={
                    "test_results": {
                        "fire_extinguishers": "failed" if is_overdue else "passed",
                        "hose_reels": "pending" if is_overdue else "passed",
                        "emergency_lights": "failed" if is_overdue else "passed",
                        "smoke_detectors": "pending" if is_overdue else "passed",
                        "sprinkler_system": "failed" if is_overdue else "passed"
                    },
                    "inspector": "Mike Wilson",
                    "compliance_score": 45,
                    "overdue": is_overdue,
                    "critical_issues": is_overdue
                },
                created_by=user.id,
                created_at=session_date
            )
            session.add(test_session)
        
        session.commit()
        print(f"✅ Created 10 test sessions for Building C (5 overdue)")
    
    # Create 20 evidence items (5 missing attestation)
    test_sessions = session.query(TestSession).filter(TestSession.building_id == building.id).all()
    evidence_count = session.query(Evidence).join(TestSession).filter(TestSession.building_id == building.id).count()
    
    if evidence_count < 20:
        evidence_types = [
            "fire_extinguisher_photo", "hose_reel_inspection", "emergency_light_test",
            "smoke_detector_check", "sprinkler_head_photo"
        ]
        
        for i in range(20):
            session_obj = test_sessions[i % len(test_sessions)]
            evidence_type = evidence_types[i % len(evidence_types)]
            missing_attestation = i in [15, 16, 17, 18, 19]  # Last 5 items missing attestation
            
            content = f"demo_evidence_c_{i}_{evidence_type}_{session_obj.id}"
            worm_hash = hashlib.sha256(content.encode()).hexdigest()
            
            evidence = Evidence(
                id=uuid.uuid4(),
                session_id=session_obj.id,
                evidence_type=evidence_type,
                file_path=f"/evidence/{session_obj.id}/{evidence_type}_{i:02d}.jpg",
                evidence_metadata={
                    "device_attestation": not missing_attestation,
                    "worm_hash": worm_hash,
                    "file_size": 1024 * 128,  # 128KB
                    "camera_model": "Basic Digital Camera",
                    "gps_coordinates": {"lat": -27.4698, "lng": 153.0251},
                    "timestamp": session_obj.created_at.isoformat(),
                    "attestation_missing": missing_attestation
                },
                checksum=worm_hash,
                created_at=session_obj.created_at
            )
            session.add(evidence)
        
        session.commit()
        print(f"✅ Created 20 evidence items for Building C (5 missing attestation)")
    
    # Create 5 critical defects (status: open, not acknowledged)
    test_sessions = session.query(TestSession).filter(TestSession.building_id == building.id).all()
    defect_count = session.query(Defect).filter(Defect.building_id == building.id).count()
    
    if defect_count < 5:
        defect_descriptions = [
            "Critical: Fire extinguisher completely discharged and needs immediate replacement",
            "Critical: Main sprinkler system valve blocked and non-functional",
            "Critical: Emergency exit door mechanism failed - door cannot be opened from inside",
            "Critical: Smoke detector system offline - no battery backup functioning",
            "Critical: Fire hose reel severely damaged with multiple leaks"
        ]
        
        for i in range(5):
            session_obj = test_sessions[i % len(test_sessions)]
            discovered_date = session_obj.created_at - timedelta(days=15 + i * 3)
            
            defect = Defect(
                id=uuid.uuid4(),
                test_session_id=session_obj.id,
                building_id=building.id,
                severity="critical",
                category="equipment_failure",
                description=defect_descriptions[i],
                as1851_rule_code=f"CR-{i+1:02d}",
                status="open",
                discovered_at=discovered_date,
                created_by=user.id,
                created_at=discovered_date
            )
            session.add(defect)
        
        session.commit()
        print(f"✅ Created 5 critical defects for Building C (open, not acknowledged)")
    
    return building


def main():
    """Main seeding function"""
    try:
        print("🌱 Starting FireAI Demo Data Seeding...")
        
        # Create database connection
        database_url = get_sync_database_url()
        engine = create_engine(database_url)
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()
        
        try:
            # Create demo user
            user = create_demo_user(session)
            
            # Create buildings with different compliance profiles
            building_a = create_building_a_perfect_compliance(session, user)
            building_b = create_building_b_good_compliance(session, user)
            building_c = create_building_c_poor_compliance(session, user)
            
            # Final summary
            print("\n" + "="*60)
            print("🎉 DEMO DATA SEEDING COMPLETED SUCCESSFULLY!")
            print("="*60)
            print(f"✅ Seeded 3 buildings:")
            print(f"   • {building_a.name} (ID: {building_a.id}) - Perfect Compliance (95%)")
            print(f"   • {building_b.name} (ID: {building_b.id}) - Good Compliance (62%)")
            print(f"   • {building_c.name} (ID: {building_c.id}) - Poor Compliance (45%)")
            
            # Count total records
            total_sessions = session.query(TestSession).join(Building).filter(
                Building.id.in_([building_a.id, building_b.id, building_c.id])
            ).count()
            
            total_evidence = session.query(Evidence).join(TestSession).join(Building).filter(
                Building.id.in_([building_a.id, building_b.id, building_c.id])
            ).count()
            
            total_defects = session.query(Defect).filter(
                Defect.building_id.in_([building_a.id, building_b.id, building_c.id])
            ).count()
            
            print(f"✅ Seeded {total_sessions} test sessions")
            print(f"✅ Seeded {total_evidence} evidence items")
            print(f"✅ Seeded {total_defects} defects")
            print("\n🏢 Building IDs for reference:")
            print(f"   Building A (Perfect): {building_a.id}")
            print(f"   Building B (Good): {building_b.id}")
            print(f"   Building C (Poor): {building_c.id}")
            print("="*60)
            
        except Exception as e:
            session.rollback()
            print(f"❌ Error during seeding: {e}")
            raise
        finally:
            session.close()
            
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
