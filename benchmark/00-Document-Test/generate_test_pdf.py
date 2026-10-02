#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Génère un manuel technique anglais (fictif) de 500 pages pour tester la
traduction FR <-> EN : titres, paragraphes, listes, procédures, tableaux,
blocs de code, notes, table des matières et signets.

Python 3 standard uniquement : le PDF est écrit à la main (aucune dépendance).

Usage :
    python generate_test_pdf.py
    python generate_test_pdf.py --pages 500 --seed 42 --out manuel.pdf
"""
import argparse
import json
import os
import random
import re
import time
import zlib

# --------------------------------------------------------------------------
# Géométrie A4 et styles
# --------------------------------------------------------------------------
PW, PH = 595.28, 841.89
ML, MR, MT, MB = 64.0, 64.0, 72.0, 64.0
CW = PW - ML - MR

INK = (0.12, 0.12, 0.14)
MUTED = (0.45, 0.47, 0.52)
ACCENT = (0.10, 0.28, 0.55)
WARN = (0.75, 0.30, 0.05)
NOTE = (0.15, 0.50, 0.35)
CODEBG = (0.95, 0.95, 0.96)
CODEINK = (0.15, 0.17, 0.22)
TABLEHEAD = (0.89, 0.92, 0.96)
GRID = (0.70, 0.72, 0.76)

DOC_TITLE = "Helios Platform - Operations Reference Manual"

# Largeurs Helvetica (AFM, caractères 32 à 126)
_W = ([278, 278, 355, 556, 556, 889, 667, 191, 333, 333, 389, 584, 278, 333, 278, 278]
      + [556] * 10
      + [278, 278, 584, 584, 584, 556, 1015]
      + [667, 667, 722, 722, 667, 611, 778, 722, 278, 500, 667, 556, 833,
         722, 778, 667, 778, 722, 667, 611, 722, 667, 944, 667, 667, 611]
      + [278, 278, 278, 469, 556, 333]
      + [556, 556, 500, 556, 556, 278, 556, 556, 222, 222, 500, 222, 833,
         556, 556, 556, 556, 333, 500, 278, 556, 500, 722, 500, 500, 500]
      + [334, 260, 334, 584])
HW = {chr(32 + i): w for i, w in enumerate(_W)}
HW.update({"•": 350, "—": 1000, "–": 556})


def esc(s):
    return s.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def tw(s, size, font="F1"):
    if font == "F4":
        return len(s) * 0.6 * size
    w = sum(HW.get(ch, 556) for ch in s) * size / 1000.0
    return w * 1.07 if font == "F2" else w


def wrap(text, size, maxw, font="F1"):
    lines, cur = [], ""
    for word in text.split():
        cand = word if not cur else cur + " " + word
        if tw(cand, size, font) <= maxw:
            cur = cand
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def slug_us(s):
    return slug(s).replace("-", "_")


# --------------------------------------------------------------------------
# Moteur de mise en page
# --------------------------------------------------------------------------
class Layout:
    def __init__(self):
        self.pages, self.page_chapter, self.toc = [], [], []
        self.cur_chapter = ""
        self.new_page()

    def new_page(self):
        self.pages.append([])
        self.page_chapter.append(self.cur_chapter)
        self.y = PH - MT

    def snapshot(self):
        return (len(self.pages), len(self.pages[-1]), self.y, len(self.toc), self.cur_chapter)

    def restore(self, snap):
        n, m, y, t, ch = snap
        del self.pages[n:]
        del self.page_chapter[n:]
        del self.pages[-1][m:]
        del self.toc[t:]
        self.y, self.cur_chapter = y, ch

    # --- primitives -------------------------------------------------------
    def _t(self, x, y, s, font="F1", size=10.5, color=INK):
        self.pages[-1].append("%.3f %.3f %.3f rg BT /%s %.2f Tf %.2f %.2f Td (%s) Tj ET"
                              % (color + (font, size, x, y, esc(s))))

    def _rect(self, x, y, w, h, color):
        self.pages[-1].append("%.3f %.3f %.3f rg %.2f %.2f %.2f %.2f re f" % (color + (x, y, w, h)))

    def _srect(self, x, y, w, h, lw, color):
        self.pages[-1].append("%.2f w %.3f %.3f %.3f RG %.2f %.2f %.2f %.2f re S"
                              % ((lw,) + color + (x, y, w, h)))

    def _line(self, x1, y1, x2, y2, lw, color):
        self.pages[-1].append("%.2f w %.3f %.3f %.3f RG %.2f %.2f m %.2f %.2f l S"
                              % ((lw,) + color + (x1, y1, x2, y2)))

    def slot(self, lh):
        if self.y - lh < MB:
            self.new_page()
        self.y -= lh
        return self.y + lh * 0.28

    # --- blocs ------------------------------------------------------------
    def chapter(self, num, title):
        self.cur_chapter = "Chapter %d - %s" % (num, title)
        if self.pages[-1]:
            self.new_page()
        else:
            self.page_chapter[-1] = self.cur_chapter
        self.y -= 40
        b = self.slot(16)
        self._t(ML, b, "CHAPTER %d" % num, "F2", 11, MUTED)
        for ln in wrap(title, 24, CW, "F2"):
            b = self.slot(30)
            self._t(ML, b, ln, "F2", 24, ACCENT)
        self.y -= 8
        self._line(ML, self.y, ML + CW, self.y, 1.2, ACCENT)
        self.y -= 18
        self.toc.append((0, "%d  %s" % (num, title), len(self.pages) - 1))

    def heading(self, text, size=13.5, keep=70, before=10, toc_level=None):
        if self.y - before - keep < MB:
            self.new_page()
        else:
            self.y -= before
        for ln in wrap(text, size, CW, "F2"):
            b = self.slot(size * 1.35)
            self._t(ML, b, ln, "F2", size, ACCENT if size > 12 else INK)
        if toc_level is not None:
            self.toc.append((toc_level, text, len(self.pages) - 1))
        self.y -= 4

    def para(self, text, font="F1", size=10.5, lh=14.5, indent=0, color=INK, after=6):
        for ln in wrap(text, size, CW - indent, font):
            b = self.slot(lh)
            self._t(ML + indent, b, ln, font, size, color)
        self.y -= after

    def bullets(self, items, numbered=False, size=10.5, lh=14.5):
        for i, it in enumerate(items, 1):
            for j, ln in enumerate(wrap(it, size, CW - 22, "F1")):
                b = self.slot(lh)
                if j == 0:
                    if numbered:
                        self._t(ML + 2, b, "%d." % i, "F2", size, ACCENT)
                    else:
                        self._t(ML + 8, b, "•", "F1", size, ACCENT)
                self._t(ML + 22, b, ln, "F1", size)
            self.y -= 2
        self.y -= 6

    def note(self, kind, text):
        col = WARN if kind == "WARNING" else NOTE
        self.y -= 4
        b = self.slot(14)
        self._t(ML + 12, b, kind, "F2", 9, col)
        self._line(ML + 3, self.y, ML + 3, self.y + 14, 2.5, col)
        for ln in wrap(text, 10, CW - 20, "F3"):
            b = self.slot(13.5)
            self._t(ML + 12, b, ln, "F3", 10, INK)
            self._line(ML + 3, self.y, ML + 3, self.y + 13.5, 2.5, col)
        self.y -= 10

    def caption(self, text):
        if self.y - 90 < MB:
            self.new_page()
        self.para(text, "F3", 9, 12, color=MUTED, after=3)

    def code(self, lines, size=8.6, lh=11.2):
        maxc = int((CW - 16) / (0.6 * size))
        out = []
        for l in lines:
            while len(l) > maxc:
                out.append(l[:maxc])
                l = "    " + l[maxc:]
            out.append(l)
        i = 0
        while i < len(out):
            avail = int((self.y - MB - 8) / lh)
            if avail < 3:
                self.new_page()
                continue
            chunk = out[i:i + avail]
            h = len(chunk) * lh + 8
            self._rect(ML, self.y - h, CW, h, CODEBG)
            yy = self.y - 4
            for l in chunk:
                yy -= lh
                self._t(ML + 8, yy + lh * 0.25, l, "F4", size, CODEINK)
            self.y -= h
            i += len(chunk)
        self.y -= 12

    def table(self, headers, rows, fracs, size=9, lh=11.5):
        ws = [f * CW for f in fracs]

        def measure(cells, font):
            wl = [wrap(str(c), size, w - 8, font) or [""] for c, w in zip(cells, ws)]
            return wl, max(len(x) for x in wl) * lh + 6

        def draw(wl, h, font, fill=None):
            x = ML
            for lines, w in zip(wl, ws):
                if fill:
                    self._rect(x, self.y - h, w, h, fill)
                self._srect(x, self.y - h, w, h, 0.5, GRID)
                yy = self.y - 3
                for ln in lines:
                    yy -= lh
                    self._t(x + 4, yy + lh * 0.25, ln, font, size, INK)
                x += w
            self.y -= h

        hl, hh = measure(headers, "F2")
        first_h = measure(rows[0], "F1")[1] if rows else 0
        if self.y - hh - first_h < MB:
            self.new_page()
        draw(hl, hh, "F2", TABLEHEAD)
        for r in rows:
            wl, h = measure(r, "F1")
            if self.y - h < MB:
                self.new_page()
                draw(hl, hh, "F2", TABLEHEAD)
            draw(wl, h, "F1")
        self.y -= 12


# --------------------------------------------------------------------------
# Contenu : 28 domaines techniques (DevOps / SRE / monétique)
# --------------------------------------------------------------------------
def T(title, comps, objs, metrics, tools, sections, code):
    return dict(title=title, components=comps, objects=objs, metrics=metrics,
                tools=tools, sections=sections, code=code)


TOPICS = [
    T("Platform Architecture Overview",
      ["API gateway", "service mesh control plane", "identity provider", "event bus", "configuration service"],
      ["architecture decision record", "service catalogue entry", "dependency map", "deployment topology"],
      ["request rate", "error ratio", "end-to-end latency", "dependency availability"],
      ["the service catalogue", "helios-cli", "the architecture portal"],
      ["Design Principles", "Logical Architecture", "Physical Deployment Model", "Service Boundaries",
       "Data Flows", "Dependency Management", "Architecture Governance", "Evolution Roadmap"],
      ["yaml", "json"]),
    T("Kubernetes Cluster Operations",
      ["kube-apiserver", "etcd cluster", "cluster autoscaler", "node pool", "kubelet"],
      ["Deployment manifest", "PodDisruptionBudget", "node taint", "namespace quota", "Helm release"],
      ["pod restart count", "node CPU saturation", "API server request latency", "etcd commit duration"],
      ["kubectl", "Helm", "k9s"],
      ["Cluster Topology", "Node Pool Management", "Namespace Strategy", "Workload Scheduling",
       "Resource Quotas and Limits", "Cluster Upgrades", "Node Draining and Maintenance", "Troubleshooting Pods"],
      ["yaml", "bash"]),
    T("Container Image Lifecycle",
      ["container registry", "image builder", "vulnerability scanner", "base image pipeline"],
      ["Dockerfile", "image tag", "software bill of materials", "image signature"],
      ["image build duration", "critical vulnerability count", "registry storage usage", "image pull latency"],
      ["Docker", "BuildKit", "Trivy", "cosign"],
      ["Base Image Policy", "Build Reproducibility", "Tagging Conventions", "Vulnerability Scanning",
       "Image Signing and Verification", "Registry Retention", "Multi-Architecture Builds"],
      ["dockerfile", "bash"]),
    T("Network Topology and Ingress",
      ["ingress controller", "load balancer", "internal DNS resolver", "egress gateway", "network policy engine"],
      ["Ingress resource", "TLS certificate", "NetworkPolicy", "DNS record", "firewall rule"],
      ["connection error rate", "TLS handshake time", "packet drop rate", "upstream response time"],
      ["NGINX", "dig", "tcpdump", "curl"],
      ["Network Segmentation", "Ingress Routing", "TLS Termination", "Internal Service Discovery",
       "Egress Control", "Rate Limiting", "Diagnosing Connectivity Issues"],
      ["nginx", "yaml", "bash"]),
    T("Persistent Storage and Volumes",
      ["CSI driver", "block storage backend", "object storage service", "snapshot controller"],
      ["PersistentVolumeClaim", "StorageClass", "volume snapshot", "retention policy"],
      ["disk utilisation", "IOPS", "read latency", "snapshot age"],
      ["kubectl", "the storage console", "fio"],
      ["Storage Classes", "Provisioning Volumes", "Expanding Volumes", "Snapshots and Clones",
       "Object Storage Buckets", "Performance Tuning", "Data Lifecycle"],
      ["yaml", "bash"]),
    T("Continuous Integration Pipelines",
      ["CI runner fleet", "pipeline orchestrator", "artifact repository", "test reporting service"],
      ["pipeline definition", "build artifact", "pipeline variable", "merge request"],
      ["pipeline duration", "job failure rate", "runner queue time", "test flakiness rate"],
      ["GitLab CI", "Jenkins", "GitHub Actions"],
      ["Pipeline Structure", "Runner Management", "Caching Strategies", "Test Stages",
       "Static Analysis", "Artifact Publication", "Pipeline Security"],
      ["gitlab", "bash"]),
    T("Continuous Delivery and GitOps",
      ["GitOps controller", "deployment repository", "progressive delivery controller", "promotion service"],
      ["Application manifest", "Kustomize overlay", "rollout strategy", "promotion request"],
      ["deployment frequency", "change failure rate", "mean time to restore", "sync drift count"],
      ["Argo CD", "Flux", "Argo Rollouts"],
      ["GitOps Principles", "Repository Layout", "Environment Promotion", "Canary Deployments",
       "Blue-Green Deployments", "Automated Rollback", "Drift Detection"],
      ["yaml"]),
    T("Infrastructure as Code with Terraform",
      ["Terraform state backend", "module registry", "plan review pipeline", "policy engine"],
      ["Terraform module", "state file", "workspace", "variable definition"],
      ["plan duration", "drifted resource count", "apply failure rate"],
      ["Terraform", "tflint", "Terragrunt", "Checkov"],
      ["Module Design", "State Management", "Workspaces and Environments", "Plan and Apply Workflow",
       "Policy as Code", "Importing Existing Resources", "Handling Drift"],
      ["hcl", "bash"]),
    T("Configuration Management with Ansible",
      ["Ansible control node", "inventory service", "AWX controller", "encrypted variables store"],
      ["playbook", "role", "inventory group", "host variable"],
      ["playbook run duration", "failed task count", "unreachable host count"],
      ["ansible-playbook", "ansible-lint", "Molecule", "AWX"],
      ["Inventory Structure", "Role Development", "Idempotency Rules", "Testing Roles with Molecule",
       "Running Playbooks Safely", "Handling Secrets", "Operating System Hardening"],
      ["ansible", "bash", "ini"]),
    T("Metrics Collection and Dashboards",
      ["Prometheus server", "Alertmanager", "Grafana instance", "remote write storage", "node exporter"],
      ["recording rule", "scrape configuration", "dashboard", "exporter"],
      ["scrape duration", "series cardinality", "ingestion rate", "query latency"],
      ["Prometheus", "Grafana", "PromQL", "Thanos"],
      ["Metrics Architecture", "Scrape Configuration", "Recording Rules", "Cardinality Management",
       "Dashboard Standards", "Long-Term Storage", "Querying Metrics"],
      ["promql", "yaml"]),
    T("Centralised Logging",
      ["log shipper", "Elasticsearch cluster", "Logstash pipeline", "Kibana instance"],
      ["index template", "ingest pipeline", "log retention policy", "structured log field"],
      ["ingestion lag", "indexing rate", "cluster heap usage", "dropped log events"],
      ["Filebeat", "Fluent Bit", "Kibana", "Elasticsearch"],
      ["Logging Standards", "Log Collection", "Parsing and Enrichment", "Index Lifecycle Management",
       "Searching Logs", "Sensitive Data in Logs", "Scaling the Log Cluster"],
      ["json", "yaml"]),
    T("Distributed Tracing",
      ["OpenTelemetry collector", "tracing backend", "sampling processor", "instrumentation library"],
      ["trace", "span attribute", "sampling policy", "service map"],
      ["span ingestion rate", "trace completeness", "sampling ratio"],
      ["OpenTelemetry", "Jaeger", "Grafana Tempo"],
      ["Tracing Concepts", "Instrumentation Guidelines", "Context Propagation", "Sampling Strategies",
       "Correlating Traces and Logs", "Analysing Latency"],
      ["yaml"]),
    T("Alerting and On-Call",
      ["alert router", "paging service", "escalation policy engine", "status page"],
      ["alerting rule", "runbook", "on-call schedule", "silence"],
      ["alert volume", "acknowledgement time", "false positive rate", "pages per shift"],
      ["Alertmanager", "PagerDuty", "Opsgenie"],
      ["Alerting Philosophy", "Severity Levels", "Writing Actionable Alerts", "On-Call Rotation",
       "Escalation Policies", "Reducing Alert Fatigue", "Silences and Maintenance Windows"],
      ["yaml"]),
    T("Incident Management",
      ["incident command process", "incident communication channel", "incident tracker", "post-incident review board"],
      ["incident record", "incident timeline", "status update", "action item"],
      ["time to detect", "time to mitigate", "incident count", "customer impact minutes"],
      ["the incident bot", "the status page", "the ticketing system"],
      ["Incident Lifecycle", "Roles and Responsibilities", "Declaring an Incident", "Communication Guidelines",
       "Mitigation Before Resolution", "Post-Incident Reviews", "Tracking Action Items"],
      ["json", "bash"]),
    T("Identity and Access Management",
      ["identity provider", "Keycloak realm", "RBAC controller", "access review workflow"],
      ["role binding", "service account", "OIDC client", "access request"],
      ["failed login rate", "privileged session count", "stale account count"],
      ["Keycloak", "kubectl", "the access portal"],
      ["Authentication Model", "Single Sign-On", "Role-Based Access Control", "Service Accounts",
       "Privileged Access", "Periodic Access Reviews", "Offboarding"],
      ["yaml", "json"]),
    T("Secrets Management",
      ["secrets manager", "Vault cluster", "external secrets operator", "key management service"],
      ["secret path", "access policy", "encryption key", "dynamic credential"],
      ["secret read rate", "lease expiry count", "seal status"],
      ["Vault", "External Secrets Operator", "sops"],
      ["Secret Classification", "Storing Secrets", "Injecting Secrets into Workloads", "Rotation Policies",
       "Dynamic Credentials", "Break-Glass Procedure", "Detecting Leaked Secrets"],
      ["hcl", "yaml", "bash"]),
    T("Network Security and Zero Trust",
      ["web application firewall", "mutual TLS mesh", "intrusion detection system", "DDoS protection layer"],
      ["security policy", "WAF rule", "certificate authority", "allow list"],
      ["blocked request count", "days until certificate expiry", "suspicious connection count"],
      ["Cloudflare", "Falco", "the WAF console"],
      ["Zero Trust Principles", "Mutual TLS", "Web Application Firewall", "DDoS Mitigation",
       "Runtime Threat Detection", "Vulnerability Management", "Security Hardening Checklist"],
      ["yaml", "bash"]),
    T("PostgreSQL Database Operations",
      ["PostgreSQL primary", "streaming replica", "connection pooler", "backup agent"],
      ["schema migration", "replication slot", "database role", "index"],
      ["replication lag", "transactions per second", "connection count", "cache hit ratio"],
      ["psql", "PgBouncer", "Patroni", "pg_dump"],
      ["Cluster Architecture", "Connection Pooling", "Schema Migrations", "Replication and Failover",
       "Vacuum and Bloat", "Query Performance", "Major Version Upgrades"],
      ["sql", "bash"]),
    T("Caching with Redis",
      ["Redis cluster", "Redis Sentinel", "cache client library"],
      ["key namespace", "eviction policy", "persistence setting", "time-to-live value"],
      ["cache hit ratio", "memory fragmentation ratio", "evicted key count", "command latency"],
      ["redis-cli", "RedisInsight"],
      ["Caching Patterns", "Key Design", "Eviction and Expiration", "Persistence Options",
       "High Availability", "Monitoring Redis"],
      ["bash", "ini"]),
    T("Messaging and Event Streaming",
      ["Kafka cluster", "RabbitMQ broker", "schema registry", "consumer group"],
      ["topic", "partition", "message schema", "dead letter queue"],
      ["consumer lag", "under-replicated partition count", "message throughput", "publish error rate"],
      ["kafka-topics", "kcat", "the RabbitMQ management interface"],
      ["Messaging Patterns", "Topic Design", "Schema Evolution", "Managing Consumer Lag",
       "Dead Letter Handling", "Delivery Guarantees", "Broker Maintenance"],
      ["bash", "json"]),
    T("Backup and Disaster Recovery",
      ["backup scheduler", "off-site backup repository", "restore validation job", "disaster recovery site"],
      ["backup policy", "recovery point", "restore runbook", "disaster recovery plan"],
      ["backup success rate", "recovery point objective", "recovery time objective", "backup size"],
      ["Velero", "restic", "pgBackRest"],
      ["Backup Strategy", "Backup Scheduling", "Encryption of Backups", "Restore Testing",
       "Disaster Recovery Plan", "Failover Exercises", "Failback"],
      ["yaml", "bash"]),
    T("Capacity Planning and Autoscaling",
      ["horizontal pod autoscaler", "cluster autoscaler", "vertical pod autoscaler", "capacity model"],
      ["scaling policy", "resource request", "capacity forecast", "load test scenario"],
      ["CPU utilisation", "memory working set", "request queue depth", "scaling event count"],
      ["k6", "the capacity dashboard", "kubectl"],
      ["Capacity Model", "Load Testing", "Horizontal Autoscaling", "Vertical Autoscaling",
       "Cluster Autoscaling", "Headroom Policy"],
      ["yaml", "bash"]),
    T("Cloud Cost Management",
      ["cost allocation service", "budget alerting service", "rightsizing recommender"],
      ["cost centre tag", "budget", "reserved capacity commitment", "cost report"],
      ["monthly spend", "cost per request", "idle resource cost", "commitment utilisation"],
      ["the cost dashboard", "Kubecost", "the billing export"],
      ["Cost Allocation", "Tagging Policy", "Budgets and Alerts", "Rightsizing",
       "Commitment Planning", "Reducing Waste"],
      ["json", "sql"]),
    T("Release Management",
      ["release train", "feature flag service", "changelog generator", "change advisory board"],
      ["release candidate", "feature flag", "release note", "change request"],
      ["lead time for changes", "release frequency", "hotfix count"],
      ["the release dashboard", "semantic-release", "the feature flag console"],
      ["Release Cadence", "Versioning Policy", "Release Candidates", "Feature Flags",
       "Change Approval", "Hotfix Process", "Communicating Releases"],
      ["bash", "yaml"]),
    T("Compliance and Auditing",
      ["audit log pipeline", "policy engine", "evidence repository", "compliance scanner"],
      ["control", "audit finding", "evidence package", "policy exception"],
      ["control coverage", "open finding count", "policy violation count"],
      ["Open Policy Agent", "the GRC platform", "kube-bench"],
      ["Regulatory Context", "Control Framework", "Audit Logging", "Policy Enforcement",
       "Evidence Collection", "Managing Exceptions", "Preparing for an Audit"],
      ["rego", "yaml"]),
    T("Payment Transaction Processing",
      ["authorization gateway", "switching engine", "settlement batch", "hardware security module",
       "fraud scoring service"],
      ["ISO 8583 message", "settlement file", "card profile", "transaction log"],
      ["authorization latency", "approval rate", "timeout rate", "settlement discrepancy count"],
      ["the transaction monitor", "the batch scheduler", "the HSM console"],
      ["Transaction Flow", "Message Formats", "Authorization Processing", "Batch Settlement",
       "Key Management", "Reconciliation", "Handling Timeouts and Reversals"],
      ["json", "sql", "bash"]),
    T("Edge and CDN Configuration",
      ["content delivery network", "edge cache", "DNS provider", "edge worker"],
      ["cache rule", "redirect rule", "DNS zone", "origin certificate"],
      ["cache hit ratio", "origin bandwidth", "edge error rate", "time to first byte"],
      ["Cloudflare", "curl", "dig"],
      ["Edge Architecture", "DNS Management", "Caching Rules", "Origin Protection",
       "Edge Functions", "Purging Content"],
      ["bash", "json"]),
    T("Service Level Objectives",
      ["SLO calculator", "error budget policy", "availability probe"],
      ["service level indicator", "service level objective", "error budget", "burn rate alert"],
      ["availability", "latency indicator", "remaining error budget", "burn rate"],
      ["Prometheus", "Sloth", "the SLO dashboard"],
      ["Defining Indicators", "Choosing Objectives", "Error Budgets", "Burn Rate Alerting",
       "Reporting", "Using SLOs in Planning"],
      ["yaml", "promql"]),
]

ENVS = ["production", "staging", "pre-production", "disaster recovery", "integration", "performance testing"]
TEAMS = ["platform team", "SRE team", "security team", "database administration team",
         "release management team", "network team", "application owners", "on-call engineer"]
FREQS = ["every five minutes", "every hour", "once a day", "once a week", "after every deployment",
         "at the beginning of each sprint", "every quarter"]
FREQS2 = ["twice a year", "every quarter", "within thirty days of each minor release",
          "as soon as a security patch is published", "during the annual maintenance window"]
DURS = ["five minutes", "ten minutes", "fifteen minutes", "thirty minutes", "one hour", "two hours", "four hours"]

SENTENCES = [
    "Before modifying the {c}, operators must confirm that the {env} environment is healthy and that no change freeze is in effect.",
    "The {c} exposes the {m} metric, which should remain below {num} under normal load.",
    "When the {m} exceeds the configured threshold for more than {dur}, an alert is routed to the {team}.",
    "All changes to the {o} must be reviewed by at least two members of the {team} before they are merged.",
    "In the {env} environment, the {c} runs with {n} replicas distributed across three availability zones.",
    "Operators should use {t} to inspect the current state of the {o} rather than editing resources by hand.",
    "If the {c} becomes unresponsive, the first step is to collect diagnostic data before attempting a restart.",
    "The default timeout for requests handled by the {c} is {sec} seconds; this value can be overridden per service.",
    "A rollback must be possible at any time, which is why every change to the {o} is versioned and stored in Git.",
    "Capacity reviews for the {c} take place {freq}, and the results are documented in the operations wiki.",
    "Misconfiguration of the {o} is the most common root cause of incidents affecting the {c}.",
    "The {team} owns the {c} and acts as the escalation point for any issue that cannot be resolved within {dur}.",
    "Logs produced by the {c} are retained for {days} days and are indexed to support audit queries.",
    "It is strongly recommended to validate the {o} in the staging environment before promoting it to production.",
    "Automated tests verify that the {c} still meets its latency budget of {ms} milliseconds at the 99th percentile.",
    "Access to the administration interface of the {c} is restricted to engineers who hold the appropriate role.",
    "The {o} is reconciled {freq} by {t}, which detects and corrects configuration drift.",
    "During peak periods, the {m} may temporarily increase by up to {pct} percent without affecting end users.",
    "Any manual intervention on the {c} must be recorded in the change log together with a ticket reference.",
    "The {c} depends on the {c2}; consequently, an outage of the {c2} will also degrade the {c}.",
    "To reduce the blast radius of a faulty release, changes to the {o} are rolled out progressively.",
    "Health checks for the {c} are executed every {sec} seconds and must succeed {n} consecutive times.",
    "The {team} publishes a monthly report that summarises the availability of the {c} and the main incidents.",
    "Encryption in transit is mandatory for all traffic between the {c} and its clients.",
    "Where possible, the {o} should be generated from templates instead of being written from scratch.",
    "The {m} is aggregated per namespace, which makes it possible to identify noisy neighbours quickly.",
    "Operators must never store credentials in the {o}; secrets are injected at runtime by the secrets manager.",
    "A known limitation of the {c} is that it cannot be resized online, so a maintenance window is required.",
    "Performance regressions are detected by comparing the {m} before and after each deployment.",
    "The {c} is upgraded {freq2}, following the vendor support calendar and internal security requirements.",
    "Each {o} carries labels that identify its owner, its cost centre and its data classification.",
    "The current design favours simplicity over flexibility, because the {team} must be able to operate the {c} under pressure.",
    "Experience shows that most outages of the {c} are caused by changes rather than by hardware failures.",
    "For this reason, the {o} is treated as code and goes through the same review process as application code.",
    "The {c} is deployed in active-active mode, so the loss of a single zone does not interrupt the service.",
    "Dashboards for the {c} display the {m} alongside the deployment markers of the last seven days.",
    "If the {m} cannot be collected, the alert is treated as critical, since the absence of data hides real problems.",
    "New engineers are expected to shadow the {team} for two on-call rotations before operating the {c} alone.",
    "Every exception to this rule must be approved by the {team} and reviewed again after {days} days.",
    "The configuration of the {c} is split into a common baseline and a small set of environment-specific overrides.",
    "Requests that exceed the rate limit of the {c} receive an HTTP 429 response and should be retried with backoff.",
    "Changes that affect the {o} are announced in the operations channel at least one business day in advance.",
    "The {c} writes structured logs in JSON format, which allows each field to be searched independently.",
    "When in doubt, operators should prefer a controlled restart of the {c} over an emergency configuration change.",
    "Synthetic probes call the {c} {freq} from three regions in order to measure availability from the user perspective.",
    "The {t} documentation describes additional options, but only the options listed in this manual are supported.",
    "A dedicated runbook exists for each alert raised by the {c}, and it is linked directly from the alert message.",
    "Resource requests for the {c} are reviewed whenever the {m} changes by more than {pct} percent over a week.",
    "Data handled by the {c} is classified as confidential and must not leave the {env} environment.",
    "The {c} supports graceful shutdown, which allows in-flight requests to complete before the process exits.",
    "Version {ver} of the {c} introduced breaking changes in the {o}, which are described in the migration notes.",
    "Load tests reproduce {pct} percent more traffic than the highest peak observed during the previous year.",
    "Ownership of the {o} is recorded in the service catalogue so that incidents can be routed without delay.",
    "The {team} reviews this procedure {freq2} and updates it after every significant incident.",
]

SECTION_INTROS = [
    "This section explains how the {team} manages {sec} for the {c}.",
    "The guidance on {sec} below applies to all environments, including {env}.",
    "{Sec} is a recurring source of questions from application teams; this section clarifies the expected practices.",
    "This section describes the standard approach to {sec} and the reasons behind the main design choices.",
    "The practices described in this section were defined after several incidents related to {sec}.",
]

RULES = [
    "Every change to the {o} must reference an approved ticket.",
    "Never apply changes directly in the {env} environment without going through the pipeline.",
    "Keep the {m} visible on the main dashboard of the {c}.",
    "Use {t} in read-only mode when investigating an issue.",
    "Document every manual action in the incident timeline or in the change log.",
    "Prefer small, incremental changes to large, infrequent ones.",
    "Make sure that a tested rollback path exists before starting any change.",
    "Do not disable alerts for the {c} without creating a time-limited silence.",
    "Store configuration in Git and treat the repository as the single source of truth.",
    "Review the {o} with a colleague from the {team} before merging.",
    "Remove temporary access rights as soon as the operation is complete.",
    "Validate the {o} automatically in the pipeline before any human review.",
    "Tag every resource with its owner and its cost centre.",
    "Escalate to the {team} if the issue is not understood within {dur}.",
    "Keep at least {pct} percent of headroom on the {c} at all times.",
    "Check the release notes of the {c} before every upgrade.",
    "Do not reuse credentials across environments.",
    "Communicate the expected impact to the application owners before the maintenance window.",
]

STEPS = [
    "Connect to the bastion host with your personal SSH key and open a session on the {env} cluster.",
    "Run {t} to list the current {o} and save the output to a file for later comparison.",
    "Verify on the monitoring dashboard that the {m} is within its normal range.",
    "Announce the start of the operation in the operations channel and reference the change ticket.",
    "Create a snapshot of the {o} so that the previous state can be restored if necessary.",
    "Apply the change through the approved pipeline; do not apply it manually from a workstation.",
    "Wait until all replicas of the {c} report a ready status.",
    "Confirm that no new errors appear in the logs of the {c} during the next {dur}.",
    "Compare the {m} with the value recorded before the change.",
    "Run the smoke tests for the services that depend on the {c}.",
    "If any check fails, stop immediately and follow the rollback procedure described in this section.",
    "Remove any temporary access or silence created for the operation.",
    "Update the change ticket with the result of the operation and close it.",
    "Notify the {team} that the procedure is complete.",
    "Record the duration of the operation so that future maintenance windows can be estimated accurately.",
]

NOTES = [
    "The values given in this section are defaults. Some services override them, and the effective value can be checked with {t}.",
    "This procedure has been tested in the staging environment. Differences in production are limited to the number of replicas.",
    "The {team} maintains a list of frequently asked questions about the {c} in the operations wiki.",
    "When the {c} is upgraded, the dashboards may show a short gap in the {m}. This is expected and does not require any action.",
    "If you are unsure about the impact of a change, ask for a second review rather than postponing the change indefinitely.",
    "Historical values of the {m} are kept for thirteen months, which allows year-over-year comparisons.",
]

WARNINGS = [
    "Deleting the {o} cannot be undone. Always create a snapshot first and confirm the target environment twice.",
    "Restarting all replicas of the {c} at the same time will cause a complete outage. Restart them one at a time.",
    "Do not change the {o} during a declared incident unless the incident commander explicitly approves it.",
    "Running this command against the {env} environment requires an approved change request.",
    "Disabling encryption on the {c}, even temporarily, is a violation of the security policy.",
    "A misconfigured {o} can silently drop traffic. Always verify the {m} after applying the change.",
]

SUMMARY = [
    "The {c} is owned by the {team}, which is also the escalation point.",
    "Changes to the {o} are versioned, reviewed and deployed through the pipeline.",
    "The {m} is the primary signal used to assess the health of the {c}.",
    "Every procedure must include a tested rollback path.",
    "Manual actions are recorded with a ticket reference.",
    "Capacity and configuration are reviewed {freq2}.",
]

PARAMS = [
    ("timeout_seconds", lambda r: str(r.choice([5, 10, 15, 30, 60])),
     "Maximum time, in seconds, that the {c} waits for a response before failing the request."),
    ("max_connections", lambda r: str(r.choice([100, 250, 500, 1000, 2000])),
     "Upper limit of concurrent connections accepted by the {c}."),
    ("replicas", lambda r: str(r.choice([2, 3, 4, 6])),
     "Number of instances of the {c} running in each availability zone."),
    ("log_level", lambda r: r.choice(["info", "warn", "debug"]),
     "Verbosity of the logs; use debug only for short investigations."),
    ("retry_limit", lambda r: str(r.choice([3, 5, 7])),
     "Number of retries performed before an operation is reported as failed."),
    ("retry_backoff_ms", lambda r: str(r.choice([100, 200, 500])),
     "Initial delay between two retries; the delay doubles after each attempt."),
    ("cache_ttl_seconds", lambda r: str(r.choice([30, 60, 300, 900])),
     "Duration for which responses are kept in the local cache."),
    ("batch_size", lambda r: str(r.choice([50, 100, 500, 1000])),
     "Number of records processed in a single batch."),
    ("tls_min_version", lambda r: r.choice(["1.2", "1.3"]),
     "Minimum TLS protocol version accepted by the {c}."),
    ("metrics_port", lambda r: str(r.choice([9090, 9100, 9187, 8081])),
     "Port on which the {c} exposes its Prometheus metrics."),
    ("drain_timeout_seconds", lambda r: str(r.choice([30, 60, 120])),
     "Time allowed for in-flight requests to complete during a graceful shutdown."),
    ("audit_enabled", lambda r: r.choice(["true", "false"]),
     "Enables the audit trail for administrative operations."),
]

TROUBLE = [
    ("The {m} increases steadily over several hours.", "A memory or connection leak in a recent release.",
     "Compare with the previous release and roll back if the trend is confirmed."),
    ("Requests to the {c} return HTTP 503 errors.", "No healthy replica is available behind the load balancer.",
     "Check the readiness probes and the recent events of the {c}."),
    ("The {c} restarts repeatedly.", "The container exceeds its memory limit and is terminated.",
     "Increase the memory limit after analysing the working set."),
    ("Deployments of the {o} remain pending.", "The cluster does not have enough free capacity.",
     "Check the autoscaler logs and the pending pod events."),
    ("Clients report TLS handshake failures.", "An expired or incomplete certificate chain.",
     "Renew the certificate and reload the {c}."),
    ("Alerts are not delivered to the {team}.", "A routing rule or a silence matches the alert by mistake.",
     "Review the active silences and test the routing tree."),
    ("Latency of the {c} doubles after a deployment.", "A configuration change disabled the local cache.",
     "Restore the previous {o} and compare the two versions."),
    ("The {m} is missing from the dashboard.", "The exporter cannot reach the metrics endpoint.",
     "Check the network policy and the scrape configuration."),
]


class Ctx:
    def __init__(self, rnd, topic):
        self.r, self.t = rnd, topic

    def vals(self, sec=""):
        r, t = self.r, self.t
        c, c2 = r.sample(t["components"], 2)
        return dict(c=c, c2=c2, o=r.choice(t["objects"]), m=r.choice(t["metrics"]), t=r.choice(t["tools"]),
                    env=r.choice(ENVS), team=r.choice(TEAMS), freq=r.choice(FREQS), freq2=r.choice(FREQS2),
                    dur=r.choice(DURS), n=r.choice([2, 3, 4, 5, 6]),
                    num=r.choice([50, 80, 200, 500, 1000, 5000]), sec=r.choice([5, 10, 15, 30, 60]),
                    days=r.choice([30, 60, 90, 180, 365]), ms=r.choice([50, 100, 150, 250, 400, 800]),
                    pct=r.choice([10, 15, 20, 25, 30, 40]),
                    ver="%d.%d" % (r.randint(1, 9), r.randint(0, 20)),
                    sec_lc=sec.lower(), Sec=sec)

    def fill(self, tpl, sec=""):
        v = self.vals(sec)
        s = tpl.replace("{sec}", "{sec_lc}").format(**v)
        return s[0].upper() + s[1:]

    def sentences(self, k, sec=""):
        return " ".join(self.fill(s, sec) for s in self.r.sample(SENTENCES, k))


# --- générateurs de code --------------------------------------------------
def code_block(kind, ctx):
    r, t = ctx.r, ctx.t
    c = r.choice(t["components"])
    s, su = slug(c), slug_us(c)
    ns = slug(t["title"].split()[0])
    env = slug(r.choice(ENVS))
    n = r.choice([2, 3, 4, 6])
    ver = "%d.%d.%d" % (r.randint(1, 5), r.randint(0, 30), r.randint(0, 9))
    if kind == "yaml":
        v = r.randint(0, 3)
        if v == 0:
            return "Deployment manifest for the %s" % c, [
                "apiVersion: apps/v1", "kind: Deployment", "metadata:", "  name: %s" % s,
                "  namespace: %s" % ns, "  labels:", "    app.kubernetes.io/name: %s" % s,
                "    app.kubernetes.io/part-of: helios", "spec:", "  replicas: %d" % n,
                "  strategy:", "    type: RollingUpdate", "    rollingUpdate:", "      maxUnavailable: 1",
                "      maxSurge: 1", "  selector:", "    matchLabels:", "      app.kubernetes.io/name: %s" % s,
                "  template:", "    metadata:", "      labels:", "        app.kubernetes.io/name: %s" % s,
                "    spec:", "      containers:", "        - name: %s" % s,
                "          image: registry.helios.internal/%s:%s" % (s, ver), "          resources:",
                "            requests:", "              cpu: %dm" % r.choice([100, 250, 500]),
                "              memory: %dMi" % r.choice([256, 512, 1024]), "            limits:",
                "              memory: %dMi" % r.choice([1024, 2048]), "          readinessProbe:",
                "            httpGet:", "              path: /healthz", "              port: 8080",
                "            periodSeconds: %d" % r.choice([5, 10])]
        if v == 1:
            return "Alerting rule for the %s" % c, [
                "groups:", "  - name: %s.rules" % s, "    rules:", "      - alert: %sHighErrorRate" % su.title().replace("_", ""),
                "        expr: |", '          sum(rate(http_requests_total{job="%s",code=~"5.."}[5m]))' % s,
                '            / sum(rate(http_requests_total{job="%s"}[5m])) > 0.0%d' % (s, r.randint(1, 5)),
                "        for: %dm" % r.choice([5, 10, 15]), "        labels:", "          severity: %s" % r.choice(["warning", "critical"]),
                "          team: %s" % slug(r.choice(TEAMS)), "        annotations:",
                '          summary: "Error rate of the %s is above the threshold"' % c,
                "          runbook_url: https://wiki.helios.internal/runbooks/%s" % s]
        if v == 2:
            return "Horizontal autoscaling policy for the %s" % c, [
                "apiVersion: autoscaling/v2", "kind: HorizontalPodAutoscaler", "metadata:",
                "  name: %s" % s, "  namespace: %s" % ns, "spec:", "  scaleTargetRef:",
                "    apiVersion: apps/v1", "    kind: Deployment", "    name: %s" % s,
                "  minReplicas: %d" % n, "  maxReplicas: %d" % (n * 4), "  metrics:", "    - type: Resource",
                "      resource:", "        name: cpu", "        target:", "          type: Utilization",
                "          averageUtilization: %d" % r.choice([60, 65, 70, 75]), "  behavior:",
                "    scaleDown:", "      stabilizationWindowSeconds: %d" % r.choice([300, 600])]
        return "GitOps application definition for the %s" % c, [
            "apiVersion: argoproj.io/v1alpha1", "kind: Application", "metadata:", "  name: %s-%s" % (s, env),
            "  namespace: argocd", "spec:", "  project: helios", "  source:",
            "    repoURL: https://git.helios.internal/deploy/%s.git" % s, "    targetRevision: main",
            "    path: overlays/%s" % env, "  destination:", "    server: https://kubernetes.default.svc",
            "    namespace: %s" % ns, "  syncPolicy:", "    automated:", "      prune: true", "      selfHeal: true",
            "    syncOptions:", "      - CreateNamespace=false"]
    if kind == "bash":
        pool = [
            "kubectl -n %s get pods -l app.kubernetes.io/name=%s -o wide" % (ns, s),
            "kubectl -n %s logs deploy/%s --since=15m | grep -i error | tail -n 40" % (ns, s),
            "kubectl -n %s rollout status deploy/%s --timeout=300s" % (ns, s),
            "kubectl -n %s describe pod -l app.kubernetes.io/name=%s" % (ns, s),
            "kubectl -n %s rollout undo deploy/%s" % (ns, s),
            "curl -sS -o /dev/null -w '%%{http_code} %%{time_total}\\n' https://%s.helios.internal/healthz" % s,
            "helios-cli %s status --env %s" % (s, env),
            "helios-cli %s config diff --env %s --against previous" % (s, env),
            "systemctl status %s --no-pager" % s,
            "journalctl -u %s --since '1 hour ago' --no-pager | tail -n 50" % s,
            "df -h /var/lib/%s && free -m" % s,
            "ss -tanp | grep -c ESTAB",
        ]
        lines = ["#!/usr/bin/env bash", "set -euo pipefail", "", "# Inspect the %s in the %s environment" % (c, env)]
        for cmd in r.sample(pool, r.randint(4, 7)):
            lines += [cmd]
        return "Diagnostic commands for the %s" % c, lines
    if kind == "json":
        d = {"service": s, "environment": env, "replicas": n,
             "timeouts": {"connect_ms": r.choice([500, 1000, 2000]), "read_ms": r.choice([2000, 5000, 10000])},
             "retry": {"max_attempts": r.choice([3, 5]), "backoff_ms": r.choice([100, 250, 500])},
             "features": {"audit_log": True, "strict_tls": True, "maintenance_mode": False},
             "owner": slug(r.choice(TEAMS)), "version": ver}
        return "Runtime configuration of the %s" % c, json.dumps(d, indent=2).splitlines()
    if kind == "hcl":
        return "Terraform module call for the %s" % c, [
            'module "%s" {' % su,
            '  source = "git::https://git.helios.internal/infra/modules/%s.git?ref=v%s"' % (s, ver), "",
            '  name          = "%s-%s"' % (s, env), '  environment   = "%s"' % env,
            "  replicas      = %d" % n, '  instance_type = "%s"' % r.choice(["cx32", "cx42", "m6i.large", "e2-standard-4"]),
            "", "  tags = {", '    owner       = "%s"' % slug(r.choice(TEAMS)),
            '    cost_centre = "CC-%d"' % r.randint(1000, 9999), '    managed_by  = "terraform"', "  }", "}", "",
            'output "%s_endpoint" {' % su, "  value       = module.%s.endpoint" % su,
            '  description = "Internal endpoint of the %s"' % c, "}"]
    if kind == "sql":
        qs = [["-- Long-running queries",
               "SELECT pid, usename, state, now() - query_start AS duration, left(query, 60) AS query",
               "FROM pg_stat_activity",
               "WHERE state <> 'idle' AND now() - query_start > interval '%d minutes'" % r.choice([1, 5, 10]),
               "ORDER BY duration DESC;"],
              ["-- Replication lag in bytes",
               "SELECT client_addr, state, pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS lag_bytes",
               "FROM pg_stat_replication;"],
              ["-- Largest tables", "SELECT relname, pg_size_pretty(pg_total_relation_size(relid)) AS total_size",
               "FROM pg_catalog.pg_statio_user_tables", "ORDER BY pg_total_relation_size(relid) DESC", "LIMIT %d;" % r.choice([10, 20])],
              ["-- Daily volume by status", "SELECT date_trunc('day', created_at) AS day, status, count(*) AS total",
               "FROM %s_events" % su, "WHERE created_at > now() - interval '%d days'" % r.choice([7, 14, 30]),
               "GROUP BY 1, 2", "ORDER BY 1, 2;"]]
        lines = []
        for q in r.sample(qs, 2):
            lines += q + [""]
        return "SQL queries used to analyse the %s" % c, lines[:-1]
    if kind == "nginx":
        return "Reverse proxy configuration for the %s" % c, [
            "server {", "    listen 443 ssl http2;", "    server_name %s.helios.example;" % s, "",
            "    ssl_certificate     /etc/ssl/helios/%s.crt;" % s, "    ssl_certificate_key /etc/ssl/helios/%s.key;" % s,
            "    ssl_protocols       TLSv1.2 TLSv1.3;", "",
            "    limit_req zone=api burst=%d nodelay;" % r.choice([20, 50, 100]), "",
            "    location / {", "        proxy_pass http://%s_upstream;" % su,
            "        proxy_set_header Host $host;", "        proxy_set_header X-Request-ID $request_id;",
            "        proxy_read_timeout %ds;" % r.choice([30, 60, 120]), "    }", "}"]
    if kind == "dockerfile":
        return "Dockerfile for the %s" % c, [
            "FROM registry.helios.internal/base/python:3.12-slim AS build", "WORKDIR /src",
            "COPY requirements.lock .", "RUN pip install --no-cache-dir --require-hashes -r requirements.lock",
            "COPY . .", "", "FROM registry.helios.internal/base/python:3.12-slim",
            "RUN useradd --uid 10001 --create-home app", "USER 10001", "WORKDIR /app",
            "COPY --from=build /usr/local/lib/python3.12 /usr/local/lib/python3.12", "COPY --from=build /src /app",
            "EXPOSE 8080", 'HEALTHCHECK CMD ["python", "-m", "app.healthcheck"]', 'ENTRYPOINT ["python", "-m", "app"]']
    if kind == "gitlab":
        return "Pipeline definition for the %s" % c, [
            "stages: [lint, test, build, scan, deploy]", "", "variables:", '  IMAGE: "$CI_REGISTRY_IMAGE/%s"' % s, "",
            "test:", "  stage: test", "  script:", "    - make test", "  artifacts:", "    reports:",
            "      junit: reports/junit.xml", "", "build:", "  stage: build", "  script:",
            '    - docker build -t "$IMAGE:$CI_COMMIT_SHORT_SHA" .', '    - docker push "$IMAGE:$CI_COMMIT_SHORT_SHA"', "",
            "scan:", "  stage: scan", "  script:", '    - trivy image --exit-code 1 --severity CRITICAL "$IMAGE:$CI_COMMIT_SHORT_SHA"',
            "", "deploy_%s:" % env.replace("-", "_"), "  stage: deploy", "  environment: %s" % env,
            "  when: manual", "  script:", "    - helios-cli %s deploy --env %s --version $CI_COMMIT_SHORT_SHA" % (s, env)]
    if kind == "ansible":
        return "Playbook applied to the %s hosts" % c, [
            "- name: Configure the %s" % c, "  hosts: %s" % su, "  become: true", "  serial: %d" % r.choice([1, 2]),
            "  tasks:", "    - name: Install the required packages", "      ansible.builtin.package:",
            "        name: [chrony, auditd, %s]" % s, "        state: present", "",
            "    - name: Deploy the configuration file", "      ansible.builtin.template:",
            "        src: %s.conf.j2" % s, "        dest: /etc/%s/%s.conf" % (s, s), "        mode: '0640'",
            "      notify: Restart %s" % s, "", "  handlers:", "    - name: Restart %s" % s,
            "      ansible.builtin.service:", "        name: %s" % s, "        state: restarted"]
    if kind == "ini":
        return "Configuration file of the %s" % c, [
            "[server]", "listen_address = 0.0.0.0", "port = %d" % r.choice([6379, 8080, 8443, 9000]),
            "max_connections = %d" % r.choice([500, 1000, 2000]), "", "[logging]", "level = info", "format = json",
            "", "[limits]", "timeout_seconds = %d" % r.choice([15, 30, 60]), "memory_limit_mb = %d" % r.choice([512, 1024, 4096]),
            "", "[security]", "tls_enabled = true", "tls_min_version = 1.2"]
    if kind == "promql":
        return "PromQL queries for the %s" % c, [
            "# Error ratio over five minutes",
            'sum(rate(http_requests_total{job="%s",code=~"5.."}[5m]))' % s,
            '  / sum(rate(http_requests_total{job="%s"}[5m]))' % s, "",
            "# 99th percentile latency",
            'histogram_quantile(0.99, sum by (le) (rate(http_request_duration_seconds_bucket{job="%s"}[5m])))' % s, "",
            "# Instances that stopped reporting", 'max_over_time(up{job="%s"}[10m]) == 0' % s]
    if kind == "rego":
        return "Admission policy enforced on the %s" % c, [
            "package helios.admission", "", "import rego.v1", "", "deny contains msg if {",
            '    input.request.kind.kind == "Deployment"', "    container := input.request.object.spec.template.spec.containers[_]",
            '    not startswith(container.image, "registry.helios.internal/")',
            '    msg := sprintf("image %v is not pulled from the internal registry", [container.image])', "}", "",
            "deny contains msg if {", '    input.request.kind.kind == "Deployment"',
            "    not input.request.object.metadata.labels.owner",
            '    msg := "every deployment must declare an owner label"', "}"]
    return "Example", ["# no example"]


# --- générateurs de tableaux ---------------------------------------------
def table_block(ctx, cn, tn):
    r, t = ctx.r, ctx.t
    c = r.choice(t["components"])
    kind = r.randint(0, 4)
    if kind == 0:
        rows = [["%s.%s" % (slug_us(c), name), gen(r), desc.format(c=c)]
                for name, gen, desc in r.sample(PARAMS, r.randint(5, 8))]
        return "Table %d.%d - Main configuration parameters of the %s" % (cn, tn, c), \
               ["Parameter", "Default", "Description"], rows, [0.36, 0.14, 0.50]
    if kind == 1:
        rows = []
        for m in t["metrics"]:
            w = r.choice([60, 70, 75, 80])
            rows.append([m, "> %d %%" % w if r.random() < 0.5 else "> %d ms" % (w * 5),
                         "> %d %%" % min(w + 15, 98) if r.random() < 0.5 else "> %d ms" % (w * 10),
                         ctx.fill(r.choice(["Notify the {team} and open a ticket.",
                                            "Page the on-call engineer and follow the runbook.",
                                            "Check recent changes to the {o}.",
                                            "Scale out the {c} and investigate the cause."]))])
        return "Table %d.%d - Alert thresholds" % (cn, tn), \
               ["Metric", "Warning", "Critical", "Expected action"], rows, [0.28, 0.14, 0.14, 0.44]
    if kind == 2:
        rows = [[e, str(r.choice([1, 2, 3, 4, 6])), "%dm" % r.choice([250, 500, 1000, 2000]),
                 "%d Mi" % r.choice([512, 1024, 2048, 4096]),
                 r.choice(["Any time", "Business hours", "Tuesday and Thursday, 20:00-23:00", "Approved window only"])]
                for e in ENVS]
        return "Table %d.%d - Sizing of the %s per environment" % (cn, tn, c), \
               ["Environment", "Replicas", "CPU request", "Memory request", "Change window"], rows, \
               [0.24, 0.12, 0.16, 0.18, 0.30]
    if kind == 3:
        roles = ["Platform", "SRE", "Security", "App owners"]
        rows = []
        for act in r.sample(t["sections"], min(6, len(t["sections"]))):
            vals = [r.choice(["R", "C", "I"]) for _ in roles]
            vals[r.randrange(len(roles))] = "A"
            rows.append([act] + vals)
        return "Table %d.%d - Responsibility matrix (R: responsible, A: accountable, C: consulted, I: informed)" % (cn, tn), \
               ["Activity"] + roles, rows, [0.40, 0.15, 0.15, 0.15, 0.15]
    rows = [[ctx.fill(a), ctx.fill(b), ctx.fill(cc)] for a, b, cc in r.sample(TROUBLE, r.randint(4, 6))]
    return "Table %d.%d - Troubleshooting guide" % (cn, tn), \
           ["Symptom", "Probable cause", "Resolution"], rows, [0.32, 0.32, 0.36]


VARIANTS = ["Advanced {s}", "{s} in Practice", "{s}: Case Studies", "Troubleshooting {s}", "Automating {s}"]


def chapter_blocks(rnd, cn, topic, round_no):
    """Produit la suite des blocs d'un chapitre (fonctions appliquées au Layout)."""
    ctx = Ctx(rnd, topic)
    title = topic["title"] if round_no == 0 else "%s: Advanced Operations" % topic["title"]
    sections = topic["sections"] if round_no == 0 else \
        [rnd.choice(VARIANTS).format(s=s) for s in topic["sections"]]

    yield lambda L: L.chapter(cn, title)
    intro = ("This chapter describes %s within the Helios platform. It is intended for platform engineers, "
             "site reliability engineers and on-call responders who operate the %s and the related services. "
             % (title.lower(), rnd.choice(topic["components"])))
    yield lambda L, p=intro + ctx.sentences(3): L.para(p)
    lst = "The chapter is organised as follows: " + ", ".join(s.lower() for s in sections[:-1]) + \
          ", and finally " + sections[-1].lower() + "."
    yield lambda L, p=lst + " " + ctx.sentences(2): L.para(p)

    tn = en = 0
    for sn, sec in enumerate(sections, 1):
        yield lambda L, h="%d.%d  %s" % (cn, sn, sec): L.heading(h, toc_level=1)
        p = ctx.fill(rnd.choice(SECTION_INTROS), sec) + " " + ctx.sentences(rnd.randint(3, 5), sec)
        yield lambda L, p=p: L.para(p)
        for _ in range(rnd.randint(1, 2)):
            yield lambda L, p=ctx.sentences(rnd.randint(3, 6), sec): L.para(p)

        parts = rnd.sample(["rules", "procedure", "table", "code", "note", "extra"], rnd.randint(3, 5))
        sub = 0
        for part in parts:
            if part == "rules":
                yield lambda L: L.para("The following rules apply:", after=3)
                items = [ctx.fill(x) for x in rnd.sample(RULES, rnd.randint(4, 6))]
                yield lambda L, it=items: L.bullets(it)
            elif part == "procedure":
                sub += 1
                verb = rnd.choice(["Restarting", "Scaling", "Upgrading", "Reconfiguring", "Validating",
                                   "Migrating", "Recovering", "Decommissioning", "Onboarding a new service on"])
                h = "%d.%d.%d  Procedure: %s the %s" % (cn, sn, sub, verb, rnd.choice(topic["components"]))
                yield lambda L, h=h: L.heading(h, size=11.5, keep=50, before=6)
                yield lambda L, p=ctx.sentences(2, sec): L.para(p)
                k = rnd.randint(6, 10)
                steps = [ctx.fill(x) for x in [STEPS[0]] + rnd.sample(STEPS[1:-3], k - 3) + STEPS[-3:-1]]
                yield lambda L, st=steps: L.bullets(st, numbered=True)
            elif part == "table":
                tn += 1
                cap, hd, rows, fr = table_block(ctx, cn, tn)
                yield lambda L, cap=cap: L.caption(cap)
                yield lambda L, hd=hd, rows=rows, fr=fr: L.table(hd, rows, fr)
            elif part == "code":
                en += 1
                cap, lines = code_block(rnd.choice(topic["code"]), ctx)
                yield lambda L, cap="Example %d.%d - %s" % (cn, en, cap): L.caption(cap)
                yield lambda L, lines=lines: L.code(lines)
                yield lambda L, p=ctx.sentences(2, sec): L.para(p)
            elif part == "note":
                if rnd.random() < 0.5:
                    yield lambda L, x=ctx.fill(rnd.choice(NOTES)): L.note("NOTE", x)
                else:
                    yield lambda L, x=ctx.fill(rnd.choice(WARNINGS)): L.note("WARNING", x)
            else:
                yield lambda L, p=ctx.sentences(rnd.randint(4, 6), sec): L.para(p)
        yield lambda L, p=ctx.sentences(rnd.randint(2, 3), sec): L.para(p)

    yield lambda L, h="%d.%d  Chapter Summary" % (cn, len(sections) + 1): L.heading(h, toc_level=1)
    yield lambda L: L.para("The key points of this chapter are the following:", after=3)
    yield lambda L, it=[ctx.fill(x) for x in rnd.sample(SUMMARY, 5)]: L.bullets(it)


def filler_blocks(rnd):
    ctx = Ctx(rnd, rnd.choice(TOPICS))
    while True:
        yield lambda L, p=ctx.sentences(rnd.randint(2, 4)): L.para(p)


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------
def build_content(budget, seed):
    rnd = random.Random(seed)
    L = Layout()
    cn, round_no = 0, 0
    overflow = False
    while not overflow:
        for topic in TOPICS:
            cn += 1
            for blk in chapter_blocks(rnd, cn, topic, round_no):
                snap = L.snapshot()
                blk(L)
                if len(L.pages) > budget:
                    L.restore(snap)
                    overflow = True
                    break
            if overflow:
                break
        round_no += 1
    # Remplit la dernière page avec des paragraphes courts
    for blk in filler_blocks(rnd):
        snap = L.snapshot()
        blk(L)
        if len(L.pages) > budget:
            L.restore(snap)
            break
    while len(L.pages) < budget:  # sécurité (cas très improbable)
        L.new_page()
    return L


def build_toc(entries, first_content_page):
    T = Layout()
    T.y -= 10
    b = T.slot(30)
    T._t(ML, b, "Contents", "F2", 24, ACCENT)
    T.y -= 14
    for level, text, idx in entries:
        page = str(first_content_page + idx)
        if level == 0:
            font, size, lh, indent = "F2", 10.5, 18, 0
            T.y -= 4
        else:
            font, size, lh, indent = "F1", 9.5, 13.5, 18
        b = T.slot(lh)
        T._t(ML + indent, b, text, font, size)
        pw = tw(page, size, font)
        T._t(ML + CW - pw, b, page, font, size)
        x0 = ML + indent + tw(text, size, font) + 6
        x1 = ML + CW - pw - 6
        if x1 > x0:
            dots = "." * int((x1 - x0) / tw(".", size))
            T._t(x1 - tw(dots, size), b, dots, "F1", size, MUTED)
    return T


def title_page(total):
    L = Layout()
    L._rect(0, PH - 300, PW, 300, ACCENT)
    L._t(ML, PH - 140, "HELIOS PLATFORM", "F2", 14, (0.80, 0.86, 0.95))
    L._t(ML, PH - 185, "Operations Reference Manual", "F2", 30, (1, 1, 1))
    L._t(ML, PH - 215, "Infrastructure, reliability, security and payment operations", "F1", 13, (0.88, 0.92, 0.98))
    L._t(ML, PH - 380, "Version 4.2  -  %d pages" % total, "F2", 12, INK)
    L._t(ML, PH - 400, "Prepared by the Helios Platform Engineering group", "F1", 11, MUTED)
    y = 220
    for ln in wrap("This is a synthetic test document generated for machine translation benchmarking "
                   "(English to French and French to English). All product names, figures, procedures and "
                   "organisations described in this manual are fictional.", 10, CW, "F3"):
        L._t(ML, y, ln, "F3", 10, MUTED)
        y -= 14
    return L


def decorate(pages, page_chapter, total):
    """Ajoute en-tête et pied de page à chaque page (sauf la couverture)."""
    out = []
    for i, ops in enumerate(pages):
        p = i + 1
        extra = []
        if p > 1:
            def t(x, y, s, f, sz, col):
                extra.append("%.3f %.3f %.3f rg BT /%s %.2f Tf %.2f %.2f Td (%s) Tj ET" % (col + (f, sz, x, y, esc(s))))
            t(ML, PH - 42, DOC_TITLE, "F1", 8, MUTED)
            ch = page_chapter[i]
            if ch:
                t(ML + CW - tw(ch, 8), PH - 42, ch, "F1", 8, MUTED)
            extra.append("0.50 w %.3f %.3f %.3f RG %.2f %.2f m %.2f %.2f l S" % (GRID + (ML, PH - 50, ML + CW, PH - 50)))
            label = "Page %d of %d" % (p, total)
            t((PW - tw(label, 8.5)) / 2, 34, label, "F1", 8.5, MUTED)
            t(ML, 34, "Version 4.2", "F1", 8.5, MUTED)
        out.append(ops + extra)
    return out


def write_pdf(pages, outlines, path, title):
    n = len(pages)
    objs = {}
    objs[1] = b"<< /Type /Catalog /Pages 2 0 R /Outlines 7 0 R /PageMode /UseOutlines >>"
    fonts = ["Helvetica", "Helvetica-Bold", "Helvetica-Oblique", "Courier"]
    for i, f in enumerate(fonts):
        objs[3 + i] = ("<< /Type /Font /Subtype /Type1 /BaseFont /%s /Encoding /WinAnsiEncoding >>" % f).encode()
    k = len(outlines)
    first_item = 8
    page_obj0 = first_item + k
    page_ids = [page_obj0 + 2 * i for i in range(n)]
    objs[2] = ("<< /Type /Pages /Kids [%s] /Count %d >>" % (" ".join("%d 0 R" % p for p in page_ids), n)).encode()
    if k:
        objs[7] = ("<< /Type /Outlines /First %d 0 R /Last %d 0 R /Count %d >>" % (first_item, first_item + k - 1, k)).encode()
    else:
        objs[7] = b"<< /Type /Outlines /Count 0 >>"
    for j, (text, pidx) in enumerate(outlines):
        oid = first_item + j
        d = "<< /Title (%s) /Parent 7 0 R" % esc(text)
        if j > 0:
            d += " /Prev %d 0 R" % (oid - 1)
        if j < k - 1:
            d += " /Next %d 0 R" % (oid + 1)
        d += " /Dest [%d 0 R /XYZ 0 %.2f 0] >>" % (page_ids[pidx], PH)
        objs[oid] = d.encode("cp1252")
    res = "<< /Font << /F1 3 0 R /F2 4 0 R /F3 5 0 R /F4 6 0 R >> >>"
    for i, ops in enumerate(pages):
        pid = page_ids[i]
        objs[pid] = ("<< /Type /Page /Parent 2 0 R /MediaBox [0 0 %.2f %.2f] /Resources %s /Contents %d 0 R >>"
                     % (PW, PH, res, pid + 1)).encode()
        data = zlib.compress("\n".join(ops).encode("cp1252"), 6)
        objs[pid + 1] = b"<< /Length %d /Filter /FlateDecode >>\nstream\n" % len(data) + data + b"\nendstream"
    info_id = page_obj0 + 2 * n
    objs[info_id] = ("<< /Title (%s) /Author (Helios Platform Engineering - synthetic) /Creator (generate_test_pdf.py) >>"
                     % esc(title)).encode()

    buf = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = {}
    for oid in sorted(objs):
        offsets[oid] = len(buf)
        buf += b"%d 0 obj\n" % oid + objs[oid] + b"\nendobj\n"
    xref = len(buf)
    maxid = max(objs)
    buf += b"xref\n0 %d\n0000000000 65535 f \n" % (maxid + 1)
    for oid in range(1, maxid + 1):
        buf += b"%010d 00000 n \n" % offsets[oid]
    buf += b"trailer\n<< /Size %d /Root 1 0 R /Info %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (maxid + 1, info_id, xref)
    with open(path, "wb") as f:
        f.write(buf)


def count_words(pages):
    rx = re.compile(r"\((.*?)(?<!\\)\) Tj")
    n = 0
    for ops in pages:
        for op in ops:
            m = rx.search(op)
            if m:
                n += len(m.group(1).split())
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pages", type=int, default=500)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                  "Helios_Operations_Manual_EN_500p.pdf"))
    a = ap.parse_args()
    t0 = time.time()

    toc_pages = 5
    for _ in range(8):
        budget = a.pages - 1 - toc_pages
        content = build_content(budget, a.seed)
        toc = build_toc(content.toc, 2 + toc_pages)
        if len(toc.pages) == toc_pages:
            break
        toc_pages = len(toc.pages)
    else:
        raise SystemExit("La table des matières ne se stabilise pas.")

    cover = title_page(a.pages)
    pages = cover.pages + toc.pages + content.pages
    chapters = [""] + ["Contents"] * len(toc.pages) + content.page_chapter
    pages = decorate(pages, chapters, len(pages))
    outlines = [("Contents", 1)] + [(text, 1 + toc_pages + idx) for lvl, text, idx in content.toc if lvl == 0]
    write_pdf(pages, outlines, a.out, DOC_TITLE)

    n_ch = sum(1 for e in content.toc if e[0] == 0)
    n_sec = sum(1 for e in content.toc if e[0] == 1)
    words = count_words(content.pages)
    print("PDF        : %s" % a.out)
    print("Pages      : %d (couverture 1 + sommaire %d + contenu %d)" % (len(pages), toc_pages, len(content.pages)))
    print("Chapitres  : %d   Sections : %d" % (n_ch, n_sec))
    print("Mots (env.): %d   Tokens estimés : ~%d" % (words, int(words * 1.35)))
    print("Taille     : %.1f Mo   Durée : %.1f s" % (os.path.getsize(a.out) / 1e6, time.time() - t0))


if __name__ == "__main__":
    main()
