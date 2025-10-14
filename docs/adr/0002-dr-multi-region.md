# ADR-0002: Disaster Recovery & Multi-Region Support
**Status:** Accepted  
**Date:** 2025-10-14  
**Authors:** Alex Wilson  
**Related Tickets:** FM-ENH-003

## Context
FireAI requires high availability and data durability. Current setup lacks multi-region redundancy for disaster recovery.

## Decision
Implement multi-region infrastructure with primary region ap-southeast-2 and secondary region to be determined.
Target RTO ≤4 hours, RPO ≤15 minutes as per docs/runbooks/dr-playbook.md.

## Consequences
- Enhanced resilience with cross-region failover capability
- Infrastructure complexity increases with multi-region management
- Additional operational costs for secondary region resources

## Alternatives Considered
- Single region with backups only (rejected: insufficient RTO/RPO)
- Multi-cloud (overkill for current scale, higher complexity)
