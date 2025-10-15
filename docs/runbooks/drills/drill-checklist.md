# Quarterly Disaster Recovery Drill Checklist
**Owner:** DevOps Team  
**Last Updated:** 2025-01-15  
**Related:** FM-ENH-002  
**Version:** 1.0

## 🎯 Drill Objectives
- **Validate RTO:** Recovery within 4 hours
- **Validate RPO:** Data loss limited to 15 minutes
- **Test Runbook Procedures:** Ensure all steps work correctly
- **Team Training:** Practice incident response procedures
- **Identify Gaps:** Find areas for improvement

## 📅 Drill Schedule
- **Frequency:** Quarterly (March, June, September, December)
- **Duration:** 4 hours maximum
- **Maintenance Window:** Scheduled during low-traffic periods
- **Next Drill:** [To be scheduled]

---

## 📋 Pre-Drill Preparation (1 Week Before)

### Schedule & Communication
- [ ] **Schedule 4-hour maintenance window**
  - Preferred: Sunday 2:00 AM - 6:00 AM local time
  - Alternative: Saturday 10:00 PM - 2:00 AM local time
  - Duration: 4 hours maximum

- [ ] **Notify stakeholders**
  - [ ] Send maintenance window notification to all teams
  - [ ] Post in #alerts channel 48 hours before
  - [ ] Update status page if applicable
  - [ ] Notify customer success team for external communications

- [ ] **Prepare communication plan**
  - [ ] Draft incident communication templates
  - [ ] Prepare status update templates
  - [ ] Set up dedicated drill communication channel
  - [ ] Identify stakeholder notification list

### Technical Preparation
- [ ] **Verify backup snapshots exist and are recent**
  ```bash
  # Run backup validation script
  ./infra/scripts/validate-backups.sh --verbose
  
  # Check Aurora snapshots (last 7 days)
  aws rds describe-db-cluster-snapshots \
    --db-cluster-identifier fire-ai-prod-cluster \
    --region ap-southeast-2 \
    --query "DBClusterSnapshots[?SnapshotCreateTime >= '$(date -d '7 days ago' --iso-8601)'].[DBClusterSnapshotIdentifier,SnapshotCreateTime,Status]"
  ```

- [ ] **Prepare staging/test environment**
  - [ ] Ensure staging environment mirrors production
  - [ ] Verify test data is available
  - [ ] Confirm staging has same backup configuration
  - [ ] Test connectivity to staging resources

- [ ] **Validate runbook procedures**
  - [ ] Review DR playbook for accuracy
  - [ ] Check all AWS CLI commands are current
  - [ ] Verify contact information is up to date
  - [ ] Test access to all required systems

### Team Preparation
- [ ] **Assign drill roles**
  - [ ] **Incident Commander:** [Name] - Overall drill coordination
  - [ ] **Technical Lead:** [Name] - Technical execution
  - [ ] **Comms Lead:** [Name] - Stakeholder communication
  - [ ] **Documentation Lead:** [Name] - Timeline and lessons learned
  - [ ] **Backup/Support:** [Name] - Additional technical support

- [ ] **Conduct pre-drill briefing**
  - [ ] Review drill objectives and timeline
  - [ ] Assign specific responsibilities
  - [ ] Confirm access to all systems
  - [ ] Review communication procedures
  - [ ] Set up drill communication channels

- [ ] **Prepare drill materials**
  - [ ] Print copy of DR playbook
  - [ ] Prepare timeline tracking sheet
  - [ ] Set up shared document for notes
  - [ ] Prepare evaluation checklist

---

## ⚡ During Drill (4-Hour Timeline)

### T+0:00 - Drill Initiation
- [ ] **Trigger simulated outage**
  - [ ] Method: [Choose one]
    - [ ] Simulate Aurora cluster failure (stop cluster)
    - [ ] Simulate ECS service failure (scale to 0)
    - [ ] Simulate DynamoDB table deletion
    - [ ] Simulate ALB target group failure
  - [ ] **Document:** Record exact time and method

- [ ] **Declare incident**
  - [ ] Incident Commander declares drill start
  - [ ] Create incident ticket/channel
  - [ ] Send initial notification to team

### T+0:05 - Team Assembly
- [ ] **Assemble response team**
  - [ ] Confirm all assigned roles are present
  - [ ] Brief team on simulated scenario
  - [ ] Establish communication protocols
  - [ ] Begin timeline documentation

- [ ] **Initial assessment**
  - [ ] Run health check commands from runbook
  - [ ] Document current system state
  - [ ] Begin impact assessment

### T+0:15 - Failure Scope Identification
- [ ] **Complete system assessment**
  - [ ] Aurora cluster status check
  - [ ] ECS service status check
  - [ ] DynamoDB table status check
  - [ ] ALB target group health check
  - [ ] API endpoint availability check

- [ ] **Determine recovery approach**
  - [ ] Select appropriate scenario from runbook
  - [ ] Estimate recovery time
  - [ ] Identify resource requirements
  - [ ] Plan recovery sequence

### T+0:30 - Recovery Procedures Initiated
- [ ] **Begin recovery process**
  - [ ] Follow selected scenario from DR playbook
  - [ ] Execute commands step-by-step
  - [ ] Document each step and timing
  - [ ] Monitor for any issues or delays

- [ ] **Communication updates**
  - [ ] Send status update to stakeholders
  - [ ] Update incident ticket with progress
  - [ ] Maintain communication channel activity

### T+2:00 - Aurora Restoration (if applicable)
- [ ] **Aurora snapshot restoration**
  - [ ] Identify latest snapshot
  - [ ] Restore cluster from snapshot
  - [ ] Create new database instance
  - [ ] Wait for cluster availability

- [ ] **Database validation**
  - [ ] Test database connectivity
  - [ ] Verify data integrity
  - [ ] Check application database connections

### T+2:30 - ECS Service Recovery
- [ ] **Service restoration**
  - [ ] Deploy new ECS tasks
  - [ ] Update task definitions if needed
  - [ ] Scale services to desired capacity
  - [ ] Monitor task health

- [ ] **Load balancer validation**
  - [ ] Check ALB target group health
  - [ ] Verify traffic routing
  - [ ] Test endpoint availability

### T+3:00 - Service Validation
- [ ] **Comprehensive testing**
  - [ ] Run smoke test procedures
  - [ ] Test critical API endpoints
  - [ ] Verify authentication flows
  - [ ] Check schema registry functionality

- [ ] **Performance validation**
  - [ ] Monitor response times
  - [ ] Check error rates
  - [ ] Validate throughput
  - [ ] Confirm monitoring is working

### T+3:30 - DNS and Final Configuration
- [ ] **DNS updates (if applicable)**
  - [ ] Update Route 53 records if needed
  - [ ] Verify DNS propagation
  - [ ] Test external connectivity

- [ ] **Final system checks**
  - [ ] Complete system health validation
  - [ ] Verify all services are operational
  - [ ] Confirm monitoring and alerting
  - [ ] Run final smoke tests

### T+4:00 - Drill Completion
- [ ] **Services restored**
  - [ ] All systems operational
  - [ ] Traffic flowing normally
  - [ ] Monitoring showing green status

- [ ] **Drill wrap-up**
  - [ ] Stop timeline documentation
  - [ ] Gather initial feedback
  - [ ] Schedule post-drill debrief
  - [ ] Send completion notification

---

## 📊 Post-Drill Activities (1 Week After)

### Immediate Post-Drill (Same Day)
- [ ] **Initial debrief session**
  - [ ] Conduct 30-minute debrief with drill team
  - [ ] Document immediate observations
  - [ ] Identify any critical issues
  - [ ] Plan detailed postmortem session

- [ ] **Document timeline**
  - [ ] Compile detailed timeline of events
  - [ ] Document actual vs. planned timing
  - [ ] Note any delays or issues encountered
  - [ ] Record lessons learned

### Post-Drill Week
- [ ] **Blameless postmortem conducted**
  - [ ] Schedule 2-hour postmortem session
  - [ ] Invite all drill participants
  - [ ] Use postmortem template from runbook
  - [ ] Focus on process improvement, not blame

- [ ] **Timeline documentation completed**
  - [ ] Finalize detailed timeline
  - [ ] Document root causes of any issues
  - [ ] Record actual RTO and RPO achieved
  - [ ] Compare with target objectives

- [ ] **Runbook gaps identified and updated**
  - [ ] Identify procedures that didn't work
  - [ ] Find missing steps or information
  - [ ] Update runbook with improvements
  - [ ] Validate updated procedures in staging

- [ ] **Lessons learned shared with team**
  - [ ] Present findings to broader team
  - [ ] Share improvements made to runbook
  - [ ] Document best practices identified
  - [ ] Update training materials if needed

- [ ] **Next drill scheduled**
  - [ ] Schedule next quarterly drill
  - [ ] Update this checklist with new date
  - [ ] Plan any changes to drill scenario
  - [ ] Assign roles for next drill

---

## 📈 Success Criteria & Metrics

### RTO Validation
- [ ] **Target:** Recovery completed within 4 hours
- [ ] **Actual:** [To be filled during drill]
- [ ] **Status:** ✅ Pass / ❌ Fail
- [ ] **Notes:** [Any observations]

### RPO Validation
- [ ] **Target:** Data loss limited to 15 minutes
- [ ] **Actual:** [To be filled during drill]
- [ ] **Status:** ✅ Pass / ❌ Fail
- [ ] **Notes:** [Any observations]

### Process Validation
- [ ] **All runbook procedures executed successfully**
- [ ] **Team communication was effective**
- [ ] **Documentation was maintained throughout**
- [ ] **Stakeholder notifications were timely**
- [ ] **Recovery process was well-coordinated**

### Technical Validation
- [ ] **All services restored and operational**
- [ ] **Data integrity maintained**
- [ ] **Performance metrics within acceptable ranges**
- [ ] **Monitoring and alerting functioning**
- [ ] **Security controls maintained**

---

## 🎭 Drill Scenarios (Rotate Quarterly)

### Q1: Aurora Database Failure
**Scenario:** Aurora cluster becomes unavailable
- Stop Aurora cluster
- Restore from latest snapshot
- Update application connections
- Validate data integrity

### Q2: ECS Service Degradation
**Scenario:** ECS tasks fail health checks
- Scale services to 0
- Rollback to previous task definition
- Scale back to normal capacity
- Validate service health

### Q3: DynamoDB Schema Registry Failure
**Scenario:** Schema registry table becomes unavailable
- Delete/disable DynamoDB table
- Verify fallback to local JSON schemas
- Restore table using PITR
- Validate schema loading

### Q4: Complete Regional Failure (Future)
**Scenario:** Simulate complete region failure
- Promote cross-region read replica
- Update Route 53 for failover
- Validate cross-region services
- Test data consistency

---

## 📞 Emergency Contacts During Drill

### Primary Contacts
- **Incident Commander:** [Phone] [Email]
- **Technical Lead:** [Phone] [Email]
- **Comms Lead:** [Phone] [Email]

### Escalation Contacts
- **DevOps Lead:** [Phone] [Email]
- **Product Owner:** [Phone] [Email]
- **AWS Support:** [Case Number] (if premium support)

### Communication Channels
- **Primary:** [Slack channel/Teams chat]
- **Backup:** [Phone conference bridge]
- **Status Updates:** [Status page/notification system]

---

## 📋 Drill Evaluation Checklist

### Team Performance
- [ ] Roles and responsibilities were clear
- [ ] Communication was effective and timely
- [ ] Decision-making was efficient
- [ ] Documentation was maintained
- [ ] Stress levels were manageable

### Technical Performance
- [ ] Recovery procedures worked as documented
- [ ] Commands executed without errors
- [ ] Recovery time met objectives
- [ ] Data integrity was maintained
- [ ] Services were fully functional after recovery

### Process Performance
- [ ] Runbook was accurate and complete
- [ ] Timeline was realistic and achievable
- [ ] Communication plan was effective
- [ ] Stakeholder notifications were timely
- [ ] Post-incident procedures were followed

### Areas for Improvement
- [ ] **Runbook Updates Needed:**
  - [ ] [Specific procedures to update]
  - [ ] [Missing information to add]
  - [ ] [Commands that need correction]

- [ ] **Process Improvements:**
  - [ ] [Communication improvements]
  - [ ] [Timeline adjustments]
  - [ ] [Role clarifications]

- [ ] **Technical Improvements:**
  - [ ] [Infrastructure changes needed]
  - [ ] [Monitoring enhancements]
  - [ ] [Backup improvements]

---

## 🔗 Related Documentation
- [DR Playbook](../dr-playbook.md)
- [Backup Validation Script](../../infra/scripts/validate-backups.sh)
- [Stack Recovery Script](../../infra/scripts/recreate-stack.sh)
- [ADR-0002: DR Multi-Region Support](../../adr/0002-dr-multi-region.md)

---

**Last Updated:** 2025-01-15  
**Next Review:** 2025-04-15  
**Owner:** DevOps Team
