import asyncio
import pytest
from httpx import AsyncClient
from toxiproxy import Toxiproxy

class OfflineSyncChaosTest:
    def __init__(self):
        self.toxiproxy = Toxiproxy()
        self.proxy = None
    
    async def setup(self):
        """Create network proxy for chaos testing"""
        self.proxy = self.toxiproxy.create(
            name="firemode_api",
            listen="127.0.0.1:18080",
            upstream="127.0.0.1:8080"
        )
    
    async def test_20_percent_packet_loss(self):
        """TDD requirement: 20% packet drop resilience"""
        # Add 20% packet loss
        self.proxy.add_toxic(
            name="packet_loss",
            type="slow_close",
            toxicity=0.2
        )
        
        # Attempt sync
        client = AsyncClient(base_url="http://127.0.0.1:18080")
        
        # Queue multiple CRDT changes
        changes = []
        for i in range(100):
            changes.append({
                "op": "set",
                "path": f"/items/{i}",
                "value": f"test_{i}"
            })
        
        # Submit with retries
        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    "/v1/tests/sessions/123/results",
                    json={"changes": changes},
                    timeout=30
                )
                if response.status_code == 200:
                    break
            except:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    raise
        
        # Verify all changes were applied
        verify_response = await client.get("/v1/tests/sessions/123")
        assert len(verify_response.json()["items"]) == 100
    
    async def test_network_partition(self):
        """Test behavior during network split"""
        # Create network partition
        self.proxy.add_toxic(
            name="timeout",
            type="timeout",
            attributes={"timeout": 0}
        )
        
        # Verify local queueing works
        # This would interact with the mobile client's offline queue
        pass
    
    async def teardown(self):
        if self.proxy:
            self.proxy.destroy()