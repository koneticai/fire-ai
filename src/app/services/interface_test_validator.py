"""
Interface test validation service.

Evaluates interface test sessions against baseline definitions and applies
AS1851 timing tolerances to produce pass/fail outcomes.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from uuid import UUID

from sqlalchemy.orm import Session

from ..models.interface_test import (
    InterfaceTestSession,
    InterfaceTestDefinition,
    InterfaceTestEvent,
)
from ..schemas.interface_test import (
    InterfaceTestValidationRequest,
    InterfaceTestValidationResponse,
)

logger = logging.getLogger(__name__)


class InterfaceTestValidator:
    """Service responsible for validating interface test execution sessions."""

    DEFAULT_TOLERANCE_SECONDS = 2.0

    def __init__(self, db: Session):
        self.db = db

    def validate(
        self,
        request: InterfaceTestValidationRequest,
        *,
        current_user_id: Optional[UUID] = None,
    ) -> InterfaceTestValidationResponse:
        """
        Validate an interface test session using the supplied request payload.

        Args:
            request: Validation request payload from API layer.
            current_user_id: Optional user ID to attribute validation to when
                request.validator_user_id is not supplied.
        """
        validator_user_id = request.validator_user_id or current_user_id
        return self.validate_session(
            session_id=request.session_id,
            tolerance_seconds=request.tolerance_seconds,
            validator_user_id=validator_user_id,
        )

    def validate_session(
        self,
        session_id: UUID,
        *,
        tolerance_seconds: Optional[float] = None,
        validator_user_id: Optional[UUID] = None,
    ) -> InterfaceTestValidationResponse:
        """
        Validate the supplied interface test session and return a response payload.

        Args:
            session_id: Interface test session identifier.
            tolerance_seconds: Optional tolerance override (defaults to service constant).
            validator_user_id: Optional user ID performing the validation.
        """
        logger.info("Validating interface test session %s", session_id)
        session = (
            self.db.query(InterfaceTestSession)
            .filter(InterfaceTestSession.id == session_id)
            .first()
        )

        if not session:
            logger.error("Interface test session %s not found", session_id)
            raise ValueError("Interface test session not found")

        definition = session.definition
        if not definition:
            # Defensive query in case relationship is not eagerly loaded
            definition = (
                self.db.query(InterfaceTestDefinition)
                .filter(InterfaceTestDefinition.id == session.definition_id)
                .first()
            )

        if not definition:
            logger.error(
                "Interface test definition %s missing for session %s",
                session.definition_id,
                session_id,
            )
            raise ValueError("Interface test definition not found")

        tolerance = (
            tolerance_seconds
            if tolerance_seconds is not None
            else self.DEFAULT_TOLERANCE_SECONDS
        )

        expected_time = (
            session.expected_response_time_s or definition.expected_response_time_s
        )
        observed_time = session.observed_response_time_s

        failure_reasons: List[str] = []
        validation_summary: str
        response_delta: Optional[float] = None
        compliance_outcome = session.compliance_outcome or "pending"

        logger.debug(
            "Validation context - expected: %s, observed: %s, tolerance: %s",
            expected_time,
            observed_time,
            tolerance,
        )

        if observed_time is None:
            failure_reasons.append("Observed response time not recorded.")
            validation_summary = (
                "Interface test failed: observed response time is missing."
            )
            compliance_outcome = "fail"
        elif expected_time is None:
            validation_summary = (
                "Interface test pending: expected response time not configured."
            )
            compliance_outcome = "pending"
        else:
            response_delta = observed_time - float(expected_time)
            within_tolerance = abs(response_delta) <= float(tolerance)

            if within_tolerance:
                validation_summary = (
                    "Interface test passed: observed response time "
                    f"{observed_time:.2f}s is within ±{tolerance:.2f}s of expected "
                    f"{expected_time:.2f}s."
                )
                compliance_outcome = "pass"
                failure_reasons = []
            else:
                validation_summary = (
                    "Interface test failed: observed response time "
                    f"{observed_time:.2f}s deviates from expected {expected_time:.2f}s "
                    f"by {response_delta:.2f}s (allowed ±{tolerance:.2f}s)."
                )
                compliance_outcome = "fail"
                if response_delta > 0:
                    failure_reasons.append(
                        "Response exceeded maximum allowable time by "
                        f"{response_delta:.2f} seconds."
                    )
                else:
                    failure_reasons.append(
                        "Response occurred earlier than expected by "
                        f"{abs(response_delta):.2f} seconds."
                    )

        validated_at = datetime.now(timezone.utc)

        session.expected_response_time_s = expected_time
        session.response_time_delta_s = response_delta
        session.validation_summary = validation_summary
        session.compliance_outcome = compliance_outcome
        session.status = "validated" if compliance_outcome != "pending" else session.status
        session.failure_reasons = failure_reasons
        session.validated_at = validated_at

        if validator_user_id:
            session.validated_by = validator_user_id

        # Persist a validation event for auditability
        validation_event = InterfaceTestEvent(
            interface_test_session_id=session.id,
            event_type="validation",
            notes=validation_summary,
            event_metadata=self._build_validation_metadata(
                compliance_outcome,
                expected_time,
                observed_time,
                response_delta,
                tolerance,
                failure_reasons,
                validator_user_id,
            ),
        )
        self.db.add(validation_event)

        self.db.commit()
        self.db.refresh(session)

        logger.info(
            "Interface test validation complete for session %s with outcome %s",
            session_id,
            compliance_outcome,
        )

        return InterfaceTestValidationResponse(
            session_id=session.id,
            compliance_outcome=session.compliance_outcome,
            expected_response_time_s=expected_time,
            observed_response_time_s=session.observed_response_time_s,
            response_time_delta_s=session.response_time_delta_s,
            tolerance_seconds=float(tolerance),
            failure_reasons=failure_reasons,
            validation_summary=validation_summary,
            validated_at=session.validated_at or validated_at,
        )

    @staticmethod
    def _build_validation_metadata(
        outcome: str,
        expected_time: Optional[float],
        observed_time: Optional[float],
        response_delta: Optional[float],
        tolerance: float,
        failure_reasons: List[str],
        validator_user_id: Optional[UUID],
    ) -> Dict[str, Any]:
        """Construct metadata payload stored with validation events."""
        metadata: Dict[str, Any] = {
            "outcome": outcome,
            "tolerance_seconds": float(tolerance),
            "failure_reasons": failure_reasons,
        }

        if expected_time is not None:
            metadata["expected_response_time_s"] = float(expected_time)
        if observed_time is not None:
            metadata["observed_response_time_s"] = float(observed_time)
        if response_delta is not None:
            metadata["response_time_delta_s"] = float(response_delta)
        if validator_user_id:
            metadata["validated_by"] = str(validator_user_id)

        return metadata
