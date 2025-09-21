from locust import HttpUser, task, between
import random
import uuid

class ResilientUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Authenticate
        self.client_id = str(uuid.uuid4())
        self.client.headers = {
            "Authorization": f"Bearer test-token"
        }
    
    def get_token(self):
        return "test-token"
    
    @task(3)
    def submit_with_failures(self):
        """Simulate intermittent failures"""
        if random.random() < 0.1:  # 10% artificial failure
            self.client.post(
                "/v1/tests/sessions/invalid/results",
                json={"changes": []},
                catch_response=True
            )
        else:
            with self.client.put(
                "/v1/tests/sessions/123",
                json={
                    "session_name": "Test Session",
                    "status": "active"
                },
                headers={"Idempotency-Key": str(uuid.uuid4()), "If-Match": "{}"},
                catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Got {response.status_code}")
    
    @task(1)
    def check_sync_status(self):
        """Verify sync state"""
        self.client.get("/v1/tests/sessions")