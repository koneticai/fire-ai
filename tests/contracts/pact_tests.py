from pact import Consumer, Provider
import json

pact = Consumer('Mobile App').has_pact_with(
    Provider('FireMode API'),
    host_name='localhost',
    port=8080
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
         'POST',
         '/v1/tests/sessions/123/results',
         headers={'Idempotency-Key': 'uuid'},
         body={
             '_sync_meta': {},
             'changes': []
         }
     )
     .will_respond_with(200))