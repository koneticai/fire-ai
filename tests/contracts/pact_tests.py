from pact import Consumer, Provider
import json
import requests
import pytest

pact = Consumer('Mobile App').has_pact_with(
    Provider('FireMode API'),
    host_name='localhost',
    port=8081  # Use non-conflicting port
)

def test_offline_bundle_contract():
    expected = {
        "session_id": "uuid",
        "timestamp": "ISO",
        "data": {
            "building": {},
            "assets": [],
            "prior_faults": []
        }
    }
    
    (pact
     .given('A test session exists')
     .upon_receiving('Request for offline bundle')
     .with_request('GET', '/v1/tests/sessions/123/offline_bundle')
     .will_respond_with(200, body=expected))
    
    with pact:
        # Test implementation
        response = requests.get(
            pact.uri + '/v1/tests/sessions/123/offline_bundle'
        )
        assert response.json() == expected

def test_crdt_submission_contract():
    (pact
     .given('A test session is active')
     .upon_receiving('CRDT result submission')
     .with_request(
         'PUT',
         '/v1/tests/sessions/123',
         headers={'Idempotency-Key': 'uuid', 'If-Match': '{}'},
         body={
             'session_name': 'Test Session',
             'status': 'active'
         }
     )
     .will_respond_with(200))
    
    with pact:
        # Test implementation
        response = requests.put(
            pact.uri + '/v1/tests/sessions/123',
            headers={'Idempotency-Key': 'uuid', 'If-Match': '{}'},
            json={'session_name': 'Test Session', 'status': 'active'}
        )
        assert response.status_code == 200