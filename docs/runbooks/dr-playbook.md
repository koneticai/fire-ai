# Disaster Recovery Playbook
**Owner:** DevOps Team  
**Last Updated:** 2025-01-15  
**Related:** FM-ENH-002  
**Version:** 2.0

## 🎯 Objectives
- **RTO (Recovery Time Objective):** ≤4 hours
- **RPO (Recovery Point Objective):** ≤15 minutes
- **Primary Region:** ap-southeast-2 (Sydney)
- **Secondary Region:** `<SECONDARY_REGION>` (Planned - FM-ENH-004)

## 📋 Pre-Incident Preparation

### Automated Backup Verification Checklist
Run daily via CI/CD or cron job:

```bash
# Verify Aurora snapshots (last 7 days)
aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier fire-ai-prod-cluster \
  --region ap-southeast-2 \
  --query "DBClusterSnapshots[?SnapshotCreateTime >= '$(date -d '7 days ago' --iso-8601)'].[DBClusterSnapshotIdentifier,SnapshotCreateTime,Status]" \
  --output table

# Verify DynamoDB point-in-time recovery
aws dynamodb describe-continuous-backups \
  --table-name fire-ai-schema-versions \
  --region ap-southeast-2 \
  --query "ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus"

# Verify S3 bucket replication (if configured)
aws s3api get-bucket-replication \
  --bucket fire-ai-schemas-backup-prod \
  --region ap-southeast-2
```

### Access Requirements
**AWS Credentials Required:**
- `AmazonRDSFullAccess` (Aurora cluster management)
- `AmazonDynamoDBFullAccess` (Schema registry table)
- `AmazonECS_FullAccess` (Service management)
- `AmazonS3FullAccess` (Backup bucket access)
- `Route53FullAccess` (DNS failover)

**IAM Roles for Service Recovery:**
- ECS task execution role with Aurora and DynamoDB access
- Lambda execution role (if future migration to serverless)

### On-Call Engineer Requirements
**Prerequisites:**
- AWS CLI v2 installed and configured
- kubectl (if using EKS) or ECS CLI
- Access to PagerDuty dashboard
- VPN access to production environment

**Contact Information:**
```
Primary On-Call: [Phone] [Email]
Secondary On-Call: [Phone] [Email]
DevOps Lead: [Phone] [Email]
Product Owner: [Phone] [Email]
```

### PagerDuty Escalation
1. **T+0:** Primary on-call notified
2. **T+15min:** Secondary on-call if no acknowledgment
3. **T+30min:** DevOps Lead escalation
4. **T+60min:** Product Owner and stakeholders

## 🚨 Incident Response Phases

### Phase 1: Assessment (0-30 minutes)

#### Aurora Database Health Check
```bash
# Check cluster status
aws rds describe-db-clusters \
  --db-cluster-identifier fire-ai-prod-cluster \
  --region ap-southeast-2 \
  --query "DBClusters[0].[DBClusterIdentifier,Status,Engine,EngineVersion,Endpoint]"

# Check cluster members
aws rds describe-db-cluster-members \
  --db-cluster-identifier fire-ai-prod-cluster \
  --region ap-southeast-2

# Check cluster events (last 2 hours)
aws rds describe-events \
  --source-identifier fire-ai-prod-cluster \
  --source-type db-cluster \
  --start-time $(date -d '2 hours ago' --iso-8601) \
  --region ap-southeast-2
```

#### ECS Service Health Verification
```bash
# List ECS services
aws ecs list-services \
  --cluster fire-ai-prod-cluster \
  --region ap-southeast-2

# Check service health
aws ecs describe-services \
  --cluster fire-ai-prod-cluster \
  --services fire-ai-api-service fire-ai-go-service \
  --region ap-southeast-2 \
  --query "services[*].[serviceName,runningCount,desiredCount,status]"

# Check task health
aws ecs list-tasks \
  --cluster fire-ai-prod-cluster \
  --service-name fire-ai-api-service \
  --desired-status RUNNING \
  --region ap-southeast-2
```

#### CloudWatch Log Analysis
```bash
# Check application logs (last 30 minutes)
aws logs filter-log-events \
  --log-group-name "/ecs/fire-ai-api" \
  --start-time $(date -d '30 minutes ago' +%s)000 \
  --region ap-southeast-2 \
  --filter-pattern "ERROR"

# Check Aurora logs
aws rds describe-db-log-files \
  --db-instance-identifier fire-ai-prod-cluster \
  --region ap-southeast-2 \
  --query "DescribeDBLogFiles[-5:].[LogFileName,LastWritten]"
```

#### Failure Scope Determination
**Database Issues:**
- Aurora cluster unavailable → Scenario A
- Individual DB instance failure → Multi-AZ failover expected

**Service Issues:**
- ECS tasks failing health checks → Scenario B
- ALB target group unhealthy → Check ECS service status

**Schema Registry Issues:**
- DynamoDB table unavailable → Scenario C (fallback to local JSON)

**Regional Issues:**
- Multiple services affected → Scenario D (cross-region failover)

### Phase 2: Recovery (30 minutes - 4 hours)

#### Scenario A: Aurora Database Failure

**Step 1: Identify Latest Snapshot**
```bash
# List recent snapshots
aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier fire-ai-prod-cluster \
  --region ap-southeast-2 \
  --query "DBClusterSnapshots[?Status=='available'] | sort_by(@, &SnapshotCreateTime) | [-1].[DBClusterSnapshotIdentifier,SnapshotCreateTime]" \
  --output table

# Export snapshot identifier
LATEST_SNAPSHOT=$(aws rds describe-db-cluster-snapshots \
  --db-cluster-identifier fire-ai-prod-cluster \
  --region ap-southeast-2 \
  --query "DBClusterSnapshots[?Status=='available'] | sort_by(@, &SnapshotCreateTime) | [-1].DBClusterSnapshotIdentifier" \
  --output text)

echo "Latest snapshot: $LATEST_SNAPSHOT"
```

**Step 2: Restore Aurora Cluster**
```bash
# Restore cluster from snapshot
aws rds restore-db-cluster-from-snapshot \
  --db-cluster-identifier fire-ai-prod-cluster-restored \
  --snapshot-identifier $LATEST_SNAPSHOT \
  --region ap-southeast-2 \
  --vpc-security-group-ids sg-xxxxxxxxx \
  --db-subnet-group-name fire-ai-prod-subnet-group \
  --port 5432

# Create primary instance
aws rds create-db-instance \
  --db-instance-identifier fire-ai-prod-restored-1 \
  --db-instance-class db.r5.large \
  --engine aurora-postgresql \
  --db-cluster-identifier fire-ai-prod-cluster-restored \
  --region ap-southeast-2

# Wait for cluster to be available
aws rds wait db-cluster-available \
  --db-cluster-identifier fire-ai-prod-cluster-restored \
  --region ap-southeast-2
```

**Step 3: Update Application Configuration**
```bash
# Get new endpoint
NEW_ENDPOINT=$(aws rds describe-db-clusters \
  --db-cluster-identifier fire-ai-prod-cluster-restored \
  --region ap-southeast-2 \
  --query "DBClusters[0].Endpoint" \
  --output text)

# Update ECS task definition with new DATABASE_URL
# (This would typically be done via CI/CD pipeline)
echo "Update DATABASE_URL to: postgresql://username:password@$NEW_ENDPOINT:5432/fireai"
```

**Step 4: DNS Failover (if applicable)**
```bash
# Update Route 53 record (if using custom domain)
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.fire-ai.com",
        "Type": "CNAME",
        "TTL": 60,
        "ResourceRecords": [{"Value": "'$NEW_ENDPOINT'"}]
      }
    }]
  }'
```

#### Scenario B: ECS Service Degradation

**Step 1: Identify Previous Task Definition**
```bash
# List task definition revisions
aws ecs list-task-definitions \
  --family-prefix fire-ai-api \
  --status ACTIVE \
  --region ap-southeast-2 \
  --query "taskDefinitionArns[-5:]"

# Get current task definition
CURRENT_TASK_DEF=$(aws ecs describe-services \
  --cluster fire-ai-prod-cluster \
  --services fire-ai-api-service \
  --region ap-southeast-2 \
  --query "services[0].taskDefinition" \
  --output text)

# Get previous revision
PREVIOUS_TASK_DEF=$(echo $CURRENT_TASK_DEF | sed 's/:\([0-9]*\)/:$((\1-1))/')
```

**Step 2: Rollback to Previous Version**
```bash
# Update service to previous task definition
aws ecs update-service \
  --cluster fire-ai-prod-cluster \
  --service fire-ai-api-service \
  --task-definition $PREVIOUS_TASK_DEF \
  --region ap-southeast-2

# Wait for deployment to complete
aws ecs wait services-stable \
  --cluster fire-ai-prod-cluster \
  --services fire-ai-api-service \
  --region ap-southeast-2
```

**Step 3: Scale Task Count (if needed)**
```bash
# Scale up tasks for increased capacity
aws ecs update-service \
  --cluster fire-ai-prod-cluster \
  --service fire-ai-api-service \
  --desired-count 4 \
  --region ap-southeast-2
```

**Step 4: Validate ALB Target Group**
```bash
# Check target group health
aws elbv2 describe-target-health \
  --target-group-arn arn:aws:elasticloadbalancing:ap-southeast-2:123456789012:targetgroup/fire-ai-api-tg/xxxxxxxxx \
  --region ap-southeast-2 \
  --query "TargetHealthDescriptions[*].[Target.Id,TargetHealth.State]"
```

#### Scenario C: DynamoDB Schema Registry Failure

**Step 1: Verify Local JSON Fallback**
```bash
# Check if local schemas exist
ls -la services/api/schemas/common/
ls -la services/api/schemas/requests/
ls -la services/api/schemas/responses/

# Verify fallback configuration
echo $FIRE_SCHEMA_SOURCE  # Should be "local+ddb" or "local-only"
```

**Step 2: DynamoDB Point-in-Time Recovery**
```bash
# Check if PITR is enabled
aws dynamodb describe-continuous-backups \
  --table-name fire-ai-schema-versions \
  --region ap-southeast-2 \
  --query "ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus"

# Restore table to point in time (example: 1 hour ago)
RESTORE_TIME=$(date -d '1 hour ago' --iso-8601)

aws dynamodb restore-table-to-point-in-time \
  --source-table-name fire-ai-schema-versions \
  --target-table-name fire-ai-schema-versions-restored \
  --restore-date-time $RESTORE_TIME \
  --region ap-southeast-2

# Wait for restore to complete
aws dynamodb wait table-exists \
  --table-name fire-ai-schema-versions-restored \
  --region ap-southeast-2
```

**Step 3: Schema Validation**
```bash
# Test schema loading
curl -X GET "https://api.fire-ai.com/v1/schemas/active" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json"

# Verify schema registry health
curl -X GET "https://api.fire-ai.com/health/schema-registry"
```

#### Scenario D: Complete Region Failure (Future Multi-Region)

**Note:** This scenario is planned for FM-ENH-004 implementation.

**Step 1: Promote Cross-Region Read Replica**
```bash
# Promote Aurora read replica in secondary region
aws rds promote-read-replica \
  --db-instance-identifier fire-ai-prod-replica-<SECONDARY_REGION> \
  --region <SECONDARY_REGION>
```

**Step 2: Route 53 Health-Check Failover**
```bash
# Update Route 53 failover policy
aws route53 change-resource-record-sets \
  --hosted-zone-id Z123456789 \
  --change-batch '{
    "Changes": [{
      "Action": "UPSERT",
      "ResourceRecordSet": {
        "Name": "api.fire-ai.com",
        "Type": "A",
        "SetIdentifier": "failover-secondary",
        "Failover": "SECONDARY",
        "AliasTarget": {
          "DNSName": "fire-ai-alb-<SECONDARY_REGION>.elb.amazonaws.com",
          "EvaluateTargetHealth": true,
          "HostedZoneId": "Z1D633PJN98FT9"
        }
      }
    }]
  }'
```

#### Scenario E: S3 Data Loss (Future Cross-Region Replication)

**Note:** This scenario is planned for FM-ENH-004 implementation.

**Step 1: Verify Cross-Region Replication**
```bash
# Check replication status
aws s3api get-bucket-replication \
  --bucket fire-ai-schemas-backup-prod \
  --region ap-southeast-2

# List objects in secondary region bucket
aws s3 ls s3://fire-ai-schemas-backup-dr/ \
  --region <SECONDARY_REGION>
```

**Step 2: Restore from Cross-Region Replica**
```bash
# Copy critical objects back to primary region
aws s3 cp s3://fire-ai-schemas-backup-dr/schemas/ \
  s3://fire-ai-schemas-backup-prod/schemas/ \
  --recursive \
  --source-region <SECONDARY_REGION>
```

### Phase 3: Validation (Final 30 minutes)

#### Smoke Test Procedures
```bash
# Health check endpoints
curl -f https://api.fire-ai.com/health
curl -f https://api.fire-ai.com/health/readiness
curl -f https://api.fire-ai.com/health/schema-registry

# Critical API endpoints
curl -X GET "https://api.fire-ai.com/v1/tests/sessions" \
  -H "Authorization: Bearer $JWT_TOKEN"

curl -X POST "https://api.fire-ai.com/v1/results" \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"test_id": "smoke-test", "status": "passed"}'
```

#### Metrics Validation Checklist
- [ ] Aurora cluster CPU < 80%
- [ ] ECS service running count = desired count
- [ ] ALB target group healthy targets > 0
- [ ] API response time < 2 seconds
- [ ] Error rate < 1%
- [ ] DynamoDB read/write capacity utilization < 80%

#### Stakeholder Communication Template
```
Subject: [RESOLVED] Fire-AI Service Recovery - [Timestamp]

Incident Summary:
- Duration: [Start Time] - [End Time]
- Root Cause: [Brief description]
- Services Affected: [List of services]
- Recovery Actions: [Summary of actions taken]

Current Status:
- All services operational
- Data integrity verified
- Monitoring normal

Next Steps:
- Postmortem scheduled: [Date/Time]
- Runbook updates: [List any updates needed]
- Follow-up actions: [List any follow-ups]

Contact: [Primary on-call engineer] [Phone] [Email]
```

## 📊 Post-Incident

### Blameless Postmortem Template

**Incident Details:**
- **Date:** [Date]
- **Duration:** [Start] - [End]
- **Severity:** [P1/P2/P3/P4]
- **Services Affected:** [List]
- **Users Impacted:** [Estimate]

**Timeline:**
```
T+0:00  - Initial alert received
T+0:05  - On-call engineer acknowledged
T+0:15  - Investigation started
T+0:30  - Root cause identified
T+1:00  - Recovery procedures initiated
T+2:30  - Services restored
T+3:00  - Validation completed
```

**Root Cause Analysis:**
- **Immediate Cause:** [What happened]
- **Contributing Factors:** [Why it happened]
- **Systemic Issues:** [Underlying problems]

**Lessons Learned:**
- **What went well:** [Positive aspects]
- **What could be improved:** [Areas for improvement]
- **Action Items:** [Specific tasks with owners and deadlines]

### Runbook Update Procedures
1. Document gaps identified during incident
2. Update procedures based on lessons learned
3. Add new scenarios if discovered
4. Validate updated procedures in staging
5. Schedule team review of changes

### Lessons Learned Documentation
- Store in `docs/runbooks/lessons-learned/`
- Use format: `YYYY-MM-DD-incident-type.md`
- Include: timeline, root cause, actions, improvements
- Share with team within 1 week of incident

## 🧪 Testing & Drills

### Quarterly DR Drill Schedule
- **Q1:** March - Aurora snapshot restoration drill
- **Q2:** June - ECS service rollback drill  
- **Q3:** September - DynamoDB PITR drill
- **Q4:** December - Full regional failover drill (when multi-region implemented)

### Success Criteria
- **RTO:** Recovery completed within 4 hours
- **RPO:** Data loss limited to 15 minutes
- **Validation:** All smoke tests pass
- **Communication:** Stakeholders notified within 30 minutes

### Drill Checklist Reference
See detailed quarterly drill procedures in:
`docs/runbooks/drills/drill-checklist.md`

---

## 🔗 Related Documentation
- [ADR-0002: DR Multi-Region Support](../adr/0002-dr-multi-region.md)
- [Quarterly Drill Checklist](./drills/drill-checklist.md)
- [Backup Validation Script](../../infra/scripts/validate-backups.sh)
- [Stack Recovery Script](../../infra/scripts/recreate-stack.sh)

## 📞 Emergency Contacts
- **Primary On-Call:** [Phone] [Email]
- **DevOps Lead:** [Phone] [Email]
- **AWS Support:** [Case Number] (if premium support)
- **PagerDuty:** [Escalation Policy URL]
