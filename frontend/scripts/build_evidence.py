"""Static F1 report adapter. No research imports, dataset readers or execution.

Only this allowlist can be read. Missing sources become unavailable; malformed
present sources fail the build. Public output contains approved reports only.
"""
import csv
import hashlib
import io
import json
import math
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = Path(__file__).resolve().parents[1]
M8 = 'reports/dafr/m8a_v1/m8a-readiness-20261107-001/'
M5 = 'reports/dafr/m5b2_v1/m5b2-retrospective-20261106-001/'
M4 = 'reports/dafr/m4a_v1/m4a-development-20261031-001/'
M6 = 'reports/dafr/m6a_v1/m6a-synthetic-20261107-001/'
M7A = 'reports/dafr/m7a_v1/m7a-synthetic-20261107-001/'
M7B = 'reports/dafr/m7b_v1/m7b-synthetic-backend-20261107-001/'
ALLOWLIST = {
    'macro': (M5+'macro_comparisons.csv', 'retrospective'),
    'machines': (M5+'comparisons.csv', 'retrospective'),
    'switches': (M5+'switch_events.csv', 'retrospective'),
    'support': (M5+'support_summary.csv', 'retrospective'),
    'adaptive-report': (M5+'completion_report.md', 'retrospective'),
    'fixed-macro': (M4+'macro_metrics.csv', 'development'),
    'fixed-report': (M4+'comparison.md', 'development'),
    'drift': (M6+'detection_summary.csv', 'synthetic'),
    'drift-report': (M6+'completion_report.md', 'synthetic'),
    'drift-backend-report': ('reports/dafr/m6b_v1/m6b-synthetic-backend-20261107-001/completion_report.md', 'synthetic'),
    'intervals-a': (M7A+'coverage_width_availability.csv', 'synthetic'),
    'interval-report-a': (M7A+'coverage_width_availability.md', 'synthetic'),
    'intervals-b': (M7B+'coverage_width_availability.csv', 'synthetic'),
    'interval-common-b': (M7B+'common_target_comparisons.csv', 'synthetic'),
    'interval-report-b': (M7B+'coverage_width_availability.md', 'synthetic'),
    'm6a-verification': (M6+'final_verification.json', 'synthetic'),
    'm6b-verification': ('reports/dafr/m6b_v1/m6b-synthetic-backend-20261107-001/preservation_and_verification.json', 'synthetic'),
    'm7a-verification': (M7A+'final_verification.json', 'synthetic'),
    'm7b-verification': (M7B+'final_verification.json', 'synthetic'),
    'm8a-verification': (M8+'regression_verification.json', 'readiness'),
    'qualification': (M8+'confirmation_metadata_inventory.json', 'readiness'),
    'research': (M8+'research_report_draft.md', 'readiness'),
    'status': (M8+'project_status_matrix.md', 'readiness'),
    'demo': (M8+'reproducibility_demo_guide.md', 'readiness'),
    'readiness': (M8+'readiness_report.md', 'readiness'),
    'figure-inventory': (M8+'figure_inventory.json', 'readiness'),
    'selector-rules': ('configs/dafr_m5a_synthetic_v1.json', 'synthetic'),
    'detector-rules': ('configs/dafr_m6a_synthetic_v1.json', 'synthetic'),
    'interval-rules': ('configs/dafr_m7a_synthetic_v1.json', 'synthetic'),
    'fig-fixed': (M4+'matched_macro_mae.png', 'development'),
    'fig-expert': (M5+'expert_matched.png', 'retrospective'),
    'fig-complete': (M5+'complete_policy_matched.png', 'retrospective'),
    'fig-nab': ('reports/figures/01_ec2_cpu_5f5533_time_series.png', 'historical'),
    'fig-missing': ('reports/figures/01_ec2_cpu_5f5533_missing_data_summary.png', 'historical'),
}
NUMERIC = {'horizon','machine_count','total_common_targets','mae','rmse','count',
 'own_complete_genuine_count','own_expert_genuine_count','origin_index','matched_pairs',
 'arima_mean_loss','xgboost_mean_loss','required_improvement','dwell_elapsed_ticks',
 'grid_ticks','known_fixture_change_tick','alarm_count','warning_entries','false_or_prechange_alarms',
 'postchange_alarms','first_postchange_alarm_tick','first_detection_delay_ticks','first_detection_delay_minutes',
 'accepted_genuine_errors','ignored_old_era_errors','final_recent_support','final_normalization_count',
 'final_era_monitor_clips','telemetry_resets','clipped_monitor_inputs_all_eras','nominal_percent',
 'attempts','issued_centers','unissued_attempts','fallback_centers','available_intervals',
 'availability_among_issued','genuine_matured_centers','genuine_available_intervals',
 'availability_among_genuine_matured','covered','empirical_coverage_available_only',
 'absolute_coverage_gap','raw_intervals_outside_cpu_range','mean_issued_width','median_issued_width',
 'mean_genuine_scored_width','mean_interval_score','missing_targets','pending',
 'common_genuine_available_count','empirical_coverage','mean_width','metric_scope'} - {'metric_scope'}


def parse_csv(payload):
    reader = csv.DictReader(io.StringIO(payload.decode('utf-8-sig')))
    if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('Missing/duplicate report columns')
    rows = []
    for raw in reader:
        if None in raw or any(v is None for v in raw.values()):
            raise ValueError('Malformed report row')
        row = {}
        for key, value in raw.items():
            if value == '': row[key] = None
            elif key in NUMERIC:
                number = float(value)
                if not math.isfinite(number): raise ValueError('Nonfinite report metric')
                row[key] = int(number) if number.is_integer() else number
            elif value in ('True','False'): row[key] = value == 'True'
            else: row[key] = value
        rows.append(row)
    return rows


def validate_rows(identifier, rows):
    required = {'macro': {'horizon','scope','policy','mae','rmse','total_common_targets'},
        'machines': {'machine','horizon','scope','policy','count','mae','rmse'},
        'switches': {'machine','horizon','origin_index','before','incumbent','matched_pairs'},
        'drift': {'fixture','horizon','alarm_count','warning_entries'},
        'intervals-a': {'fixture','policy','horizon','nominal_percent','covered','genuine_available_intervals','genuine_matured_centers','empirical_coverage_available_only'},
        'intervals-b': {'fixture','policy','horizon','nominal_percent','covered','genuine_available_intervals','genuine_matured_centers','empirical_coverage_available_only'}}
    seen = set()
    for row in rows:
        if identifier in required and not required[identifier].issubset(row): raise ValueError('Report schema changed: '+identifier)
        if 'horizon' in row and row['horizon'] not in (1,12): raise ValueError('Unsupported horizon')
        if identifier in ('macro','machines'):
            key = tuple(row.get(k) for k in ('machine','scope','horizon','policy'))
            if key in seen: raise ValueError('Duplicate comparison')
            seen.add(key)
            if row['label'] != 'RETROSPECTIVE DEVELOPMENT DIAGNOSTIC': raise ValueError('Scope mismatch')
            if any(row[k] is not None and row[k] < 0 for k in ('mae','rmse')): raise ValueError('Negative error')
        if identifier in ('intervals-a','intervals-b'):
            key = tuple(row[k] for k in ('fixture','policy','horizon','nominal_percent'))
            if key in seen: raise ValueError('Duplicate interval summary')
            seen.add(key)
            if row['nominal_percent'] not in (90,95) or row['label'] != 'SYNTHETIC ENGINEERING DIAGNOSTIC ONLY': raise ValueError('Interval scope mismatch')
            n = row['genuine_available_intervals']; covered = row['covered']
            if not 0 <= covered <= n <= row['genuine_matured_centers']: raise ValueError('Invalid genuine denominator')
            coverage = row['empirical_coverage_available_only']
            if (coverage is None) != (n == 0): raise ValueError('Undefined coverage must remain unavailable')
            if n and not math.isclose(coverage, covered/n, abs_tol=1e-12): raise ValueError('Invented coverage')
            if row['issued_centers'] + row['unissued_attempts'] != row['attempts']: raise ValueError('Forecast accounting mismatch')
            if row['available_intervals'] > row['issued_centers']: raise ValueError('Interval without center')
            for numerator, denominator, field in (('available_intervals','issued_centers','availability_among_issued'),('genuine_available_intervals','genuine_matured_centers','availability_among_genuine_matured')):
                value = row[field]; denom = row[denominator]
                if denom and not math.isclose(value,row[numerator]/denom,abs_tol=1e-12): raise ValueError('Availability mismatch')
    return rows


def validate_json(identifier, data):
    if identifier == 'qualification':
        candidates = data['candidates']
        if data['full_v2_qualified_count'] != sum(c['full_v2_qualified'] is True for c in candidates):
            raise ValueError('Qualification count differs from source candidates')
        for candidate in candidates:
            if not math.isclose(candidate['observed_coverage'],candidate['observed_bins']/1152,abs_tol=1e-12):
                raise ValueError('Qualification coverage mismatch')
    if identifier in ('selector-rules','detector-rules','interval-rules'):
        if data.get('confirmation_execution_allowed') is not False:
            raise ValueError('F1 must not expose an execution-enabled protocol')
    return data


def build(project_root=ROOT, output=FRONTEND/'public/evidence'):
    project_root = Path(project_root).resolve(); output = Path(output)
    artifacts = []
    # Remove only previously-generated allowlisted public exports; never sources.
    output.mkdir(parents=True, exist_ok=True)
    expected = {'snapshot.json'} | {key+Path(path).suffix for key,(path,_) in ALLOWLIST.items()}
    for old in output.iterdir():
        if old.name in expected and old.is_file(): old.unlink()
    for key,(relative,scope) in ALLOWLIST.items():
        path = project_root/relative
        if path.is_symlink() or path.resolve() != path: raise ValueError('Symlink source rejected')
        record = {'id':key,'path':relative,'scope':scope,'status':'unavailable','reason':'Approved artifact not present'}
        if path.is_file():
            payload = path.read_bytes()
            if len(payload) > 2*1024*1024: raise ValueError('Unexpectedly large report')
            suffix = path.suffix; record.update(status='available',reason=None,sha256=hashlib.sha256(payload).hexdigest(),url='/evidence/'+key+suffix)
            if suffix == '.csv': record['rows'] = validate_rows(key,parse_csv(payload))
            elif suffix == '.json': record['data'] = validate_json(key,json.loads(payload))
            elif suffix == '.png' and payload[:8] != b'\x89PNG\r\n\x1a\n': raise ValueError('Invalid PNG')
            (output/(key+suffix)).write_bytes(payload)
        artifacts.append(record)
    # Cross-check available figures against the existing verified inventory.
    inventory = next(a for a in artifacts if a['id']=='figure-inventory')
    if inventory['status']=='available':
        hashes = {x['path']:x['sha256'] for x in inventory['data']['figures']}
        for a in artifacts:
            if a['path'].endswith('.png') and a['status']=='available' and hashes.get(a['path']) != a['sha256']:
                raise ValueError('Figure differs from verified inventory')
    signature = hashlib.sha256(json.dumps([(a['id'],a.get('sha256')) for a in artifacts],sort_keys=True).encode()).hexdigest()
    snapshot = {'schemaVersion':1,'readOnly':True,'signature':signature,'artifacts':artifacts}
    (output/'snapshot.json').write_text(json.dumps(snapshot,indent=2,allow_nan=False)+'\n')
    if output.resolve() == (FRONTEND/'public/evidence').resolve():
        generated = FRONTEND/'src/generated'
        generated.mkdir(parents=True,exist_ok=True)
        (generated/'evidence.json').write_text(json.dumps(snapshot,indent=2,allow_nan=False)+'\n')
    return snapshot


if __name__ == '__main__':
    snapshot = build()
    print('Validated allowlisted static evidence:',sum(a['status']=='available' for a in snapshot['artifacts']),'/',len(ALLOWLIST))
