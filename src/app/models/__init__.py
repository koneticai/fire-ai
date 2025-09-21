"""
SQLAlchemy models for FireMode Compliance Platform
"""

from .users import User
from .buildings import Building
from .test_sessions import TestSession
from .evidence import Evidence
from .rtl import TokenRevocationList
from .rules import AS1851Rule, AS1851RuleBase, AS1851RuleCreate
# Import additional models
try:
    from .rules import FaultClassificationRequest, FaultClassificationResult, APIResponse
    HAS_CLASSIFICATION_MODELS = True
except ImportError:
    HAS_CLASSIFICATION_MODELS = False

__all__ = [
    "User",
    "Building", 
    "TestSession",
    "Evidence",
    "TokenRevocationList",
    "AS1851Rule",
    "AS1851RuleBase", 
    "AS1851RuleCreate"
]

if HAS_CLASSIFICATION_MODELS:
    __all__.extend(["FaultClassificationRequest", "FaultClassificationResult", "APIResponse"])