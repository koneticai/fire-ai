# Disaster Recovery Playbook
**Owner:** DevOps Team  
**Last Updated:** 2025-10-14  
**Related:** FM-ENH-002

## Objectives
- RTO ≤4 hours, RPO ≤15 minutes

## Pre-Incident
- Automated backups (Aurora snapshots 6-hourly, 7-day retention)
- Cross-region S3 replication to ap-southeast-2
- On-call access + PagerDuty escalation active

## Incident Response
- Assess metrics & logs, restore from snapshot, update stack, validate, switch DNS
- Post-incident: postmortem, update runbook, quarterly staging drill
