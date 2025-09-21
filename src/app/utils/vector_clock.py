from typing import Dict, List, Any, Optional
import json

class VectorClock:
    def __init__(self, clock: Optional[Dict[str, int]] = None):
        self.clock = clock or {}
    
    def increment(self, node_id: str) -> None:
        """Increment vector clock for a node"""
        self.clock[node_id] = self.clock.get(node_id, 0) + 1
    
    def merge(self, other: 'VectorClock') -> 'VectorClock':
        """Merge two vector clocks, taking max of each component"""
        merged = VectorClock()
        all_nodes = set(self.clock.keys()) | set(other.clock.keys())
        for node in all_nodes:
            merged.clock[node] = max(
                self.clock.get(node, 0),
                other.clock.get(node, 0)
            )
        return merged
    
    def happens_before(self, other: 'VectorClock') -> bool:
        """Check if this clock happens-before another (strict comparison)"""
        # All components must be <= and at least one must be strictly <
        has_strictly_less = False
        for node in set(self.clock.keys()) | set(other.clock.keys()):
            self_val = self.clock.get(node, 0)
            other_val = other.clock.get(node, 0)
            
            if self_val > other_val:
                return False
            elif self_val < other_val:
                has_strictly_less = True
        
        return has_strictly_less
    
    def to_json(self) -> str:
        return json.dumps(self.clock)
    
    @classmethod
    def from_json(cls, data: str) -> 'VectorClock':
        return cls(json.loads(data))