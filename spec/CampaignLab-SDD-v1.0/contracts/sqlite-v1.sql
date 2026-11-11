PRAGMA foreign_keys=ON;

CREATE TABLE workspaces (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, source_class TEXT NOT NULL CHECK(source_class IN ('SYNTHETIC','AUTHORIZED_DEIDENTIFIED')),
    authorization_note TEXT, revision INTEGER NOT NULL DEFAULT 1 CHECK(revision>=1), created_at TEXT NOT NULL,
    CHECK(source_class='SYNTHETIC' OR length(coalesce(authorization_note,''))>0)
) STRICT;
CREATE TABLE artifacts (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, kind TEXT NOT NULL,
    sha256 TEXT NOT NULL CHECK(length(sha256)=64), relative_path TEXT NOT NULL UNIQUE,
    byte_size INTEGER NOT NULL CHECK(byte_size>=0), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id), UNIQUE(workspace_id,kind,sha256)
) STRICT;
CREATE TABLE activities (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, name TEXT NOT NULL,
    bank_id TEXT, external_activity_id TEXT, description TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('OPEN','ARCHIVED')),
    current_rule_id TEXT, revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id), UNIQUE(workspace_id,bank_id,external_activity_id),
    FOREIGN KEY(workspace_id,current_rule_id) REFERENCES rule_versions(workspace_id,id)
) STRICT;
CREATE TABLE evidence (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, kind TEXT NOT NULL CHECK(kind IN ('SOURCE','CLAUSE','COMPUTATION','TRACE','PREFLIGHT','RECEIPT','SIGNATURE','EXPERIMENT','REVIEW_NOTE')),
    source_id TEXT NOT NULL, locator TEXT NOT NULL, label TEXT NOT NULL, source_class TEXT NOT NULL,
    content_digest TEXT NOT NULL CHECK(length(content_digest)=64), artifact_id TEXT NOT NULL, created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id)
) STRICT;
CREATE TABLE activity_bindings (
    workspace_id TEXT NOT NULL, activity_id TEXT NOT NULL, strategy_id TEXT NOT NULL, source_version TEXT NOT NULL,
    valid_from TEXT NOT NULL, valid_until TEXT NOT NULL CHECK(valid_until>valid_from), evidence_id TEXT NOT NULL,
    PRIMARY KEY(workspace_id,activity_id,strategy_id,source_version,valid_from),
    FOREIGN KEY(workspace_id,activity_id) REFERENCES activities(workspace_id,id),
    FOREIGN KEY(workspace_id,evidence_id) REFERENCES evidence(workspace_id,id)
) STRICT;
CREATE TABLE rule_versions (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT NOT NULL, parent_rule_id TEXT,
    label TEXT NOT NULL, template TEXT NOT NULL CHECK(template IN ('coupon_threshold','callback_priority')), source_rule_version TEXT,
    state TEXT NOT NULL CHECK(state IN ('DRAFT','CONFIRMED')), revision INTEGER NOT NULL CHECK(revision>=1),
    content_json TEXT NOT NULL CHECK(json_valid(content_json)), terms_json TEXT NOT NULL CHECK(json_valid(terms_json)),
    digest TEXT NOT NULL CHECK(length(digest)=64), created_at TEXT NOT NULL, confirmed_at TEXT, confirmation TEXT,
    CHECK((state='CONFIRMED')=(confirmed_at IS NOT NULL AND confirmation IS NOT NULL)),
    PRIMARY KEY(workspace_id,id),
    FOREIGN KEY(workspace_id,activity_id) REFERENCES activities(workspace_id,id),
    FOREIGN KEY(workspace_id,parent_rule_id) REFERENCES rule_versions(workspace_id,id)
) STRICT;
CREATE TABLE source_mappings (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, bank_id TEXT NOT NULL,
    content_json TEXT NOT NULL CHECK(json_valid(content_json)), digest TEXT NOT NULL CHECK(length(digest)=64), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id)
) STRICT;
CREATE TABLE imports (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, bank_id TEXT NOT NULL, snapshot_code TEXT NOT NULL,
    format TEXT NOT NULL CHECK(format IN ('LEGACY_SYNTHETIC_JSON','SOURCE_JSON','SOURCE_CSV')),
    state TEXT NOT NULL CHECK(state IN ('RECEIVED','CONFIGURED','VALIDATING','VALID','INVALID','PUBLISHING','PUBLISHED')),
    mapping_id TEXT, validation_digest TEXT, issue_json TEXT NOT NULL CHECK(json_valid(issue_json)),
    snapshot_id TEXT, correction_of TEXT, job_id TEXT, revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id),
    FOREIGN KEY(workspace_id,mapping_id) REFERENCES source_mappings(workspace_id,id),
    FOREIGN KEY(workspace_id,snapshot_id) REFERENCES snapshots(workspace_id,id),
    FOREIGN KEY(workspace_id,correction_of) REFERENCES snapshots(workspace_id,id),
    FOREIGN KEY(workspace_id,job_id) REFERENCES jobs(workspace_id,id)
) STRICT;
CREATE TABLE import_files (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, import_id TEXT NOT NULL, artifact_id TEXT NOT NULL,
    table_name TEXT NOT NULL, label TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id), UNIQUE(workspace_id,import_id,table_name),
    FOREIGN KEY(workspace_id,import_id) REFERENCES imports(workspace_id,id),
    FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id)
) STRICT;
CREATE TABLE snapshots (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, bank_id TEXT NOT NULL, snapshot_code TEXT NOT NULL,
    mapping_id TEXT NOT NULL, import_id TEXT, correction_of TEXT, row_count INTEGER NOT NULL CHECK(row_count>=0),
    artifact_id TEXT NOT NULL, metadata_json TEXT NOT NULL CHECK(json_valid(metadata_json)),
    digest TEXT NOT NULL CHECK(length(digest)=64), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id), UNIQUE(workspace_id,bank_id,snapshot_code),
    FOREIGN KEY(workspace_id,import_id) REFERENCES imports(workspace_id,id),
    FOREIGN KEY(workspace_id,mapping_id) REFERENCES source_mappings(workspace_id,id),
    FOREIGN KEY(workspace_id,correction_of) REFERENCES snapshots(workspace_id,id),
    FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id)
) STRICT;
CREATE TABLE cases (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT NOT NULL, parent_case_id TEXT,
    name TEXT NOT NULL, mode TEXT NOT NULL CHECK(mode IN ('SYNTHETIC','HISTORICAL')),
    state TEXT NOT NULL CHECK(state IN ('DRAFT','CONFIRMED')), revision INTEGER NOT NULL CHECK(revision>=1),
    input_json TEXT NOT NULL CHECK(json_valid(input_json)),
    expected_json TEXT CHECK(expected_json IS NULL OR json_valid(expected_json)),
    observed_original_json TEXT CHECK(observed_original_json IS NULL OR json_valid(observed_original_json)),
    observed_rule_id TEXT, action_id TEXT, digest TEXT NOT NULL CHECK(length(digest)=64), confirmation TEXT, created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id),
    FOREIGN KEY(workspace_id,activity_id) REFERENCES activities(workspace_id,id),
    FOREIGN KEY(workspace_id,parent_case_id) REFERENCES cases(workspace_id,id),
    FOREIGN KEY(workspace_id,observed_rule_id) REFERENCES rule_versions(workspace_id,id),
    FOREIGN KEY(workspace_id,action_id) REFERENCES actions(workspace_id,id)
) STRICT;
CREATE UNIQUE INDEX cases_one_confirmed_child ON cases(workspace_id,parent_case_id) WHERE parent_case_id IS NOT NULL AND state='CONFIRMED';
CREATE TABLE thresholds (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, label TEXT NOT NULL,
    values_json TEXT NOT NULL CHECK(json_valid(values_json)), digest TEXT NOT NULL CHECK(length(digest)=64), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id)
) STRICT;
CREATE TABLE analysis_results (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL,
    kind TEXT NOT NULL CHECK(kind IN ('comparison','review','diagnosis','question')),
    input_json TEXT NOT NULL CHECK(json_valid(input_json)), artifact_id TEXT NOT NULL, digest TEXT NOT NULL CHECK(length(digest)=64),
    snapshot_id TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id),
    FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id),
    FOREIGN KEY(workspace_id,snapshot_id) REFERENCES snapshots(workspace_id,id)
) STRICT;
CREATE TABLE runs (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT NOT NULL, baseline_rule_id TEXT NOT NULL, candidate_rule_id TEXT,
    snapshot_id TEXT, request_json TEXT NOT NULL CHECK(json_valid(request_json)), artifact_id TEXT NOT NULL,
    digest TEXT NOT NULL CHECK(length(digest)=64), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id),
    FOREIGN KEY(workspace_id,activity_id) REFERENCES activities(workspace_id,id),
    FOREIGN KEY(workspace_id,baseline_rule_id) REFERENCES rule_versions(workspace_id,id),
    FOREIGN KEY(workspace_id,candidate_rule_id) REFERENCES rule_versions(workspace_id,id),
    FOREIGN KEY(workspace_id,snapshot_id) REFERENCES snapshots(workspace_id,id),
    FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id)
) STRICT;
CREATE TABLE run_cases (
    workspace_id TEXT NOT NULL, run_id TEXT NOT NULL, case_id TEXT NOT NULL, case_digest TEXT NOT NULL CHECK(length(case_digest)=64),
    PRIMARY KEY(workspace_id,run_id,case_id),
    FOREIGN KEY(workspace_id,run_id) REFERENCES runs(workspace_id,id),
    FOREIGN KEY(workspace_id,case_id) REFERENCES cases(workspace_id,id)
) STRICT;
CREATE TABLE candidates (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, run_id TEXT NOT NULL, case_id TEXT NOT NULL, rule_id TEXT NOT NULL,
    case_digest TEXT NOT NULL CHECK(length(case_digest)=64), rule_digest TEXT NOT NULL CHECK(length(rule_digest)=64),
    expected_json TEXT NOT NULL CHECK(json_valid(expected_json)), review_note TEXT NOT NULL, created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id), UNIQUE(workspace_id,run_id,case_id),
    FOREIGN KEY(workspace_id,run_id,case_id) REFERENCES run_cases(workspace_id,run_id,case_id),
    FOREIGN KEY(workspace_id,rule_id) REFERENCES rule_versions(workspace_id,id)
) STRICT;
CREATE TABLE preflights (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT NOT NULL, source_batch TEXT NOT NULL,
    observed_at TEXT NOT NULL, state TEXT NOT NULL CHECK(state IN ('MATCH','REVIEW_REQUIRED')),
    artifact_id TEXT NOT NULL, digest TEXT NOT NULL CHECK(length(digest)=64), review_note TEXT,
    revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id), UNIQUE(workspace_id,activity_id,source_batch),
    FOREIGN KEY(workspace_id,activity_id) REFERENCES activities(workspace_id,id),
    FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id)
) STRICT;
CREATE TABLE preflight_rows (
    workspace_id TEXT NOT NULL, preflight_id TEXT NOT NULL, candidate_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('MATCH','DIFF','MISSING','VERSION_MISMATCH','STALE')),
    PRIMARY KEY(workspace_id,preflight_id,candidate_id),
    FOREIGN KEY(workspace_id,preflight_id) REFERENCES preflights(workspace_id,id),
    FOREIGN KEY(workspace_id,candidate_id) REFERENCES candidates(workspace_id,id)
) STRICT;
CREATE TABLE receipts (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, activity_id TEXT NOT NULL, preflight_id TEXT NOT NULL,
    source_system TEXT NOT NULL, source_release_id TEXT NOT NULL, source_version TEXT NOT NULL,
    rule_digest TEXT NOT NULL CHECK(length(rule_digest)=64), released_at TEXT NOT NULL,
    evidence_id TEXT NOT NULL, created_at TEXT NOT NULL, PRIMARY KEY(workspace_id,id),
    UNIQUE(workspace_id,activity_id,source_system,source_release_id),
    FOREIGN KEY(workspace_id,activity_id) REFERENCES activities(workspace_id,id),
    FOREIGN KEY(workspace_id,preflight_id) REFERENCES preflights(workspace_id,id),
    FOREIGN KEY(workspace_id,evidence_id) REFERENCES evidence(workspace_id,id)
) STRICT;
CREATE TABLE reports (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, review_id TEXT NOT NULL, previous_report_id TEXT,
    state TEXT NOT NULL CHECK(state IN ('DRAFT_READY','PARTIAL_DRAFT','DATA_REQUIRED','SIGNED')),
    input_json TEXT NOT NULL CHECK(json_valid(input_json)), artifact_id TEXT NOT NULL,
    digest TEXT NOT NULL CHECK(length(digest)=64), signer TEXT, signed_at TEXT, signature_evidence_id TEXT,
    revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL,
    CHECK((state='SIGNED')=(signed_at IS NOT NULL AND signer IS NOT NULL AND signature_evidence_id IS NOT NULL)),
    PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,review_id) REFERENCES analysis_results(workspace_id,id),
    FOREIGN KEY(workspace_id,previous_report_id) REFERENCES reports(workspace_id,id),
    FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id),
    FOREIGN KEY(workspace_id,signature_evidence_id) REFERENCES evidence(workspace_id,id)
) STRICT;
CREATE TABLE actions (
    workspace_id TEXT NOT NULL, id TEXT NOT NULL, review_id TEXT NOT NULL, diagnosis_id TEXT,
    title TEXT NOT NULL, owner TEXT NOT NULL, due_on TEXT NOT NULL, checkpoint_days INTEGER NOT NULL CHECK(checkpoint_days IN (30,90)),
    hypothesis TEXT NOT NULL, verification TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('OPEN','IN_PROGRESS','WAITING_VALIDATION','VERIFIED','CLOSED','CANCELLED')),
    needs_review INTEGER NOT NULL CHECK(needs_review IN (0,1)), revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id),
    FOREIGN KEY(workspace_id,review_id) REFERENCES analysis_results(workspace_id,id),
    FOREIGN KEY(workspace_id,diagnosis_id) REFERENCES analysis_results(workspace_id,id)
) STRICT;
CREATE TABLE action_followups (
    workspace_id TEXT NOT NULL, action_id TEXT NOT NULL, id TEXT NOT NULL, next_review_id TEXT NOT NULL,
    receipt_id TEXT, details_json TEXT NOT NULL CHECK(json_valid(details_json)), created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,action_id,id),
    FOREIGN KEY(workspace_id,action_id) REFERENCES actions(workspace_id,id),
    FOREIGN KEY(workspace_id,next_review_id) REFERENCES analysis_results(workspace_id,id),
    FOREIGN KEY(workspace_id,receipt_id) REFERENCES receipts(workspace_id,id)
) STRICT;
CREATE TABLE report_actions (
    workspace_id TEXT NOT NULL, report_id TEXT NOT NULL, action_id TEXT NOT NULL,
    PRIMARY KEY(workspace_id,report_id,action_id),
    FOREIGN KEY(workspace_id,report_id) REFERENCES reports(workspace_id,id),
    FOREIGN KEY(workspace_id,action_id) REFERENCES actions(workspace_id,id)
) STRICT;
CREATE TABLE exports (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, kind TEXT NOT NULL,
    subject_json TEXT NOT NULL CHECK(json_valid(subject_json)), reason TEXT NOT NULL, filename TEXT NOT NULL, artifact_id TEXT NOT NULL, created_at TEXT NOT NULL,
    PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,artifact_id) REFERENCES artifacts(workspace_id,id)
) STRICT;
CREATE TABLE jobs (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), id TEXT NOT NULL, kind TEXT NOT NULL,
    state TEXT NOT NULL CHECK(state IN ('QUEUED','RUNNING','CANCEL_REQUESTED','SUCCEEDED','FAILED','CANCELLED')),
    attempt INTEGER NOT NULL CHECK(attempt>=0), progress INTEGER NOT NULL CHECK(progress BETWEEN 0 AND 100),
    stage TEXT NOT NULL, lease_token TEXT, lease_until TEXT, retry_of TEXT, retryable INTEGER NOT NULL CHECK(retryable IN (0,1)),
    input_json TEXT NOT NULL CHECK(json_valid(input_json)), input_digest TEXT NOT NULL CHECK(length(input_digest)=64),
    result_json TEXT CHECK(result_json IS NULL OR json_valid(result_json)), problem_json TEXT CHECK(problem_json IS NULL OR json_valid(problem_json)),
    revision INTEGER NOT NULL CHECK(revision>=1), created_at TEXT NOT NULL,
    CHECK((state IN ('RUNNING','CANCEL_REQUESTED'))=(lease_token IS NOT NULL AND lease_until IS NOT NULL)),
    CHECK((state='SUCCEEDED')=(result_json IS NOT NULL)),
    PRIMARY KEY(workspace_id,id), FOREIGN KEY(workspace_id,retry_of) REFERENCES jobs(workspace_id,id)
) STRICT;
CREATE TABLE object_evidence (
    workspace_id TEXT NOT NULL, object_kind TEXT NOT NULL, object_id TEXT NOT NULL, evidence_id TEXT NOT NULL,
    PRIMARY KEY(workspace_id,object_kind,object_id,evidence_id),
    FOREIGN KEY(workspace_id,evidence_id) REFERENCES evidence(workspace_id,id)
) STRICT;
CREATE TABLE idempotency (
    scope_key TEXT NOT NULL, actor_id TEXT NOT NULL, operation TEXT NOT NULL, idem_key TEXT NOT NULL,
    request_digest TEXT NOT NULL CHECK(length(request_digest)=64), response_status INTEGER NOT NULL,
    response_json TEXT NOT NULL CHECK(json_valid(response_json)), created_at TEXT NOT NULL,
    PRIMARY KEY(scope_key,actor_id,operation,idem_key)
) STRICT;
CREATE TABLE audit (
    workspace_id TEXT NOT NULL REFERENCES workspaces(id), sequence INTEGER NOT NULL CHECK(sequence>=1),
    id TEXT NOT NULL, at TEXT NOT NULL, actor_id TEXT NOT NULL, role TEXT NOT NULL, action TEXT NOT NULL,
    target_kind TEXT NOT NULL, target_id TEXT NOT NULL, outcome TEXT NOT NULL CHECK(outcome IN ('ACCEPTED','DENIED','FAILED')),
    request_id TEXT NOT NULL, previous_digest TEXT, digest TEXT NOT NULL CHECK(length(digest)=64),
    PRIMARY KEY(workspace_id,sequence), UNIQUE(workspace_id,id)
) STRICT;
CREATE INDEX jobs_ready ON jobs(state,created_at,workspace_id,id);
CREATE INDEX snapshots_lookup ON snapshots(workspace_id,bank_id,created_at);
CREATE INDEX rules_activity ON rule_versions(workspace_id,activity_id,created_at);
CREATE INDEX analysis_snapshot ON analysis_results(workspace_id,snapshot_id,kind);
CREATE INDEX actions_due ON actions(workspace_id,state,due_on);
