# ADR-0001: Repository Foundation
**Status:** Accepted  
**Date:** 2025-10-14  
**Authors:** Alex Wilson  
**Related Tickets:** FM-ENH-001..005

## Context
Initial repository structure, CI, QA, and governance under MPKF v3.1.

## Decision
Adopt monorepo layout with services/api (Python) and src/go_service (Go).
Enable GitHub Actions CI and BugBot QA; enforce MPKF via hooks and PR template.

## Consequences
Consistent quality gates; small overhead maintaining templates & hooks.

## Alternatives Considered
Multi-repo; defer governance to later phases (rejected).
