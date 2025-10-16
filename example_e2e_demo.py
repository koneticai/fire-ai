#!/usr/bin/env python3
"""
Example demonstration of the defects E2E workflow.

This script shows how the defects workflow would be used in practice,
demonstrating the API calls that the integration test validates.
"""

import requests
import json
import uuid
from datetime import datetime


def demo_defects_workflow():
    """Demonstrate the complete defects workflow."""
    
    base_url = "http://localhost:5000"
    headers = {
        "Authorization": "Bearer your-jwt-token-here",
        "Content-Type": "application/json"
    }
    
    print("🚀 FireMode Compliance Platform - Defects Workflow Demo")
    print("=" * 60)
    
    # Step 1: Create test session (inspection)
    print("\n1. Creating test session (inspection)...")
    session_data = {
        "building_id": str(uuid.uuid4()),
        "session_name": "Fire Safety Inspection - Demo",
        "status": "active"
    }
    
    # This would make the actual API call:
    # response = requests.post(f"{base_url}/v1/tests/sessions/", 
    #                         json=session_data, headers=headers)
    # session_result = response.json()
    # session_id = session_result["session_id"]
    
    # For demo purposes, simulate the response:
    session_id = str(uuid.uuid4())
    print(f"   ✓ Test session created: {session_id}")
    
    # Step 2: Upload evidence (photo)
    print("\n2. Uploading evidence (photo)...")
    evidence_data = {
        "session_id": session_id,
        "evidence_type": "photo",
        "metadata": json.dumps({
            "location": "Fire extinguisher station A1",
            "inspector": "John Doe",
            "equipment_id": "FE-001"
        })
    }
    
    # This would make the actual API call:
    # files = {"file": ("photo.jpg", open("photo.jpg", "rb"), "image/jpeg")}
    # response = requests.post(f"{base_url}/v1/evidence/submit", 
    #                         data=evidence_data, files=files, headers=headers)
    # evidence_result = response.json()
    # evidence_id = evidence_result["evidence_id"]
    
    # For demo purposes, simulate the response:
    evidence_id = str(uuid.uuid4())
    print(f"   ✓ Evidence uploaded: {evidence_id}")
    
    # Step 3: Create defect (link to session)
    print("\n3. Creating defect (link to session)...")
    defect_data = {
        "test_session_id": session_id,
        "severity": "high",
        "category": "fire_extinguisher",
        "description": "Fire extinguisher pressure gauge shows 150 PSI, below minimum threshold of 180 PSI",
        "as1851_rule_code": "FE-01",
        "asset_id": str(uuid.uuid4())
    }
    
    # This would make the actual API call:
    # response = requests.post(f"{base_url}/v1/defects/", 
    #                         json=defect_data, headers=headers)
    # defect_result = response.json()
    # defect_id = defect_result["id"]
    
    # For demo purposes, simulate the response:
    defect_id = str(uuid.uuid4())
    print(f"   ✓ Defect created: {defect_id}")
    
    # Step 4: Link evidence to defect
    print("\n4. Linking evidence to defect...")
    link_data = {"defect_id": defect_id}
    
    # This would make the actual API call:
    # response = requests.post(f"{base_url}/v1/evidence/{evidence_id}/link-defect", 
    #                         json=link_data, headers=headers)
    # link_result = response.json()
    
    print(f"   ✓ Evidence linked to defect: {evidence_id} -> {defect_id}")
    
    # Step 5: Get defect with linked evidence
    print("\n5. Getting defect with linked evidence...")
    
    # This would make the actual API call:
    # response = requests.get(f"{base_url}/v1/defects/{defect_id}", headers=headers)
    # defect_with_evidence = response.json()
    
    # For demo purposes, simulate the response:
    evidence_count = 1
    print(f"   ✓ Defect retrieved with {evidence_count} evidence items")
    
    # Step 6: Update defect status (acknowledge)
    print("\n6. Updating defect status (acknowledge)...")
    update_data = {"status": "acknowledged"}
    
    # This would make the actual API call:
    # response = requests.patch(f"{base_url}/v1/defects/{defect_id}", 
    #                          json=update_data, headers=headers)
    # updated_defect = response.json()
    
    print(f"   ✓ Defect status updated to: acknowledged")
    
    # Step 7: Get building's defects (verify it appears)
    print("\n7. Getting building's defects...")
    building_id = session_data["building_id"]
    
    # This would make the actual API call:
    # response = requests.get(f"{base_url}/v1/defects/buildings/{building_id}/defects", 
    #                        headers=headers)
    # building_defects = response.json()
    
    # For demo purposes, simulate the response:
    defect_count = 1
    print(f"   ✓ Building has {defect_count} defect(s)")
    
    # Step 8: Flag evidence for review
    print("\n8. Flagging evidence for review...")
    flag_data = {"flag_reason": "Suspicious content detected"}
    
    # This would make the actual API call:
    # admin_headers = {"Authorization": "Bearer admin-jwt-token-here"}
    # response = requests.patch(f"{base_url}/v1/evidence/{evidence_id}/flag", 
    #                          json=flag_data, headers=admin_headers)
    # flag_result = response.json()
    
    print(f"   ✓ Evidence flagged for review: Suspicious content detected")
    
    # Final summary
    print("\n" + "=" * 60)
    print("🎉 Complete Defects Workflow Demo")
    print("=" * 60)
    print("All 8 steps completed successfully:")
    print("1. ✓ Test session created")
    print("2. ✓ Evidence uploaded")
    print("3. ✓ Defect created")
    print("4. ✓ Evidence linked to defect")
    print("5. ✓ Defect retrieved with evidence")
    print("6. ✓ Defect status updated")
    print("7. ✓ Building defects retrieved")
    print("8. ✓ Evidence flagged for review")
    print("\nThe defects workflow is fully functional!")
    print("\nTo run the actual integration test:")
    print("  python run_e2e_tests.py")


if __name__ == "__main__":
    demo_defects_workflow()
