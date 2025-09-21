from locust import HttpUser, task, between
import random

class ResilientUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        # Authenticate
        self.client.headers = {
            "Authorization": f"Bearer {self.get_token()}"
        }
    
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
            with self.client.post(
                "/v1/tests/sessions/123/results",
                json={
                    "changes": [{"op": "set", "path": "/test", "value": "data"}],
                    "_sync_meta": {"client_id": self.client_id}
                },
                headers={"Idempotency-Key": str(uuid.uuid4())},
                catch_response=True
            ) as response:
                if response.status_code != 200:
                    response.failure(f"Got {response.status_code}")
    
    @task(1)
    def check_sync_status(self):
        """Verify sync state"""
        self.client.get("/v1/tests/sessions/123/sync_status")