"""Recheck saved M4A ledgers without reopening any original suffix source."""
import argparse
import csv
from datetime import datetime, timedelta
import hashlib
import json
import math
from pathlib import Path

from .run_m4a_v1 import ROOT, PRIMARY_IDS, verify_history, write_new


def read_jsonl(path):
    with path.open() as handle:
        return [json.loads(line) for line in handle]


def audit(run_id, root=ROOT):
    root = Path(root)
    base = root / 'data/processed/dafr/m4a_development_v1' / run_id
    report = root / 'reports/dafr/m4a_v1' / run_id
    verify_history(root)
    config = json.loads((root / 'configs/dafr_m4a_execution_v1.json').read_text())
    metric_rows = json.loads((report/'forward_metrics.json').read_text())
    result = {}
    for machine in PRIMARY_IDS:
        directory = base / machine
        # This is the newly authorized, bounded copy, never the full export.
        segment = directory / 'scoped_input/authorized_1152_1612.csv'
        receipt = json.loads((directory / 'scoped_input/extraction_receipt.json').read_text())
        payload = segment.read_bytes()
        assert hashlib.sha256(payload).hexdigest() == receipt['segment_sha256']
        assert len(payload) == receipt['bytes_read']
        with segment.open(newline='') as handle:
            inputs = list(csv.DictReader(handle))
        assert len(inputs) == 460
        events = read_jsonl(directory / 'events.jsonl')
        assert all(a['record']['sequence'] < b['record']['sequence'] for a,b in zip(events, events[1:]))
        ticks = {e['record']['timestamp']: e['record'] for e in events if e['kind'] == 'tick'}
        assert list(ticks) == [r['timestamp'] for r in inputs]
        for row in inputs:
            expected = float(row['value']) if row['quality_status'] == 'valid' else None
            assert ticks[row['timestamp']]['value'] == expected
        updates = [e['record'] for e in events if e['kind'] == 'adapter_update']
        assert len(updates) == 920
        by_origin = {}
        for update in updates:
            by_origin.setdefault(update['origin'], []).append(update)
            assert update['result']['model_state_cutoff'] == update['origin']
            assert update['status'] == 'ok'
        for pair in by_origin.values():
            assert len(pair) == 2 and pair[0]['context_sha256'] == pair[1]['context_sha256']
        states = {e['record']['timestamp']:e['record'] for e in events if e['kind']=='state'}
        totals = {'decisions':0, 'scored':0, 'unavailable':0, 'pending':0, 'abstentions':0}
        own_expert = {}
        complete = {}
        for policy in ('persistence', 'arima', 'xgboost'):
            forecasts = read_jsonl(directory / policy / 'predictions.jsonl')
            outcomes = read_jsonl(directory / policy / 'outcomes.jsonl')
            assert len(forecasts) == 920
            f_by_id = {f['forecast_id']:f for f in forecasts}
            assert len(f_by_id) == 920
            o_by_id = {o['forecast_id']:o for o in outcomes}
            assert len(o_by_id) == len(outcomes)
            for h in (1,12):
                complete[policy,h] = [o for o in outcomes if o['horizon']==h and o['status']=='scored']
                own_expert[policy,h] = {(o['origin'],o['target']):o for o in complete[policy,h]
                    if policy=='persistence' or f_by_id[o['forecast_id']]['availability']=='expert'}
            for forecast in forecasts:
                origin, target = map(datetime.fromisoformat, (forecast['origin'],forecast['target']))
                assert target - origin == timedelta(minutes=5*forecast['horizon'])
                assert forecast['origin'] in ticks
                state = states[forecast['origin']]
                assert forecast['context_sha256'] == state['context_sha256']
                assert forecast['sequence'] > state['sequence']
                assert forecast['interval_status'] == 'not_implemented'
                assert forecast['lower'] is None and forecast['upper'] is None
                if policy != 'persistence':
                    assert datetime.fromisoformat(forecast['policy_selection_cutoff']) < origin
                if forecast['availability'] == 'expert':
                    assert state['learned_eligible'] and state['genuine_streak'] >= 24
                    for key in ('training_cutoff','scaling_cutoff','version_available_at'):
                        assert forecast[key] is None or datetime.fromisoformat(forecast[key]) <= origin
                if forecast['availability'] in ('fallback','baseline'):
                    assert forecast['last_genuine_age_ticks'] <= 3
                if forecast['availability'] == 'abstained':
                    assert forecast['predicted_value'] is None and forecast['forecast_id'] not in o_by_id
                    totals['abstentions'] += 1
                elif forecast['target'] in ticks:
                    assert forecast['forecast_id'] in o_by_id
                else:
                    assert forecast['forecast_id'] not in o_by_id
                    assert target > datetime.fromisoformat(inputs[-1]['timestamp'])
                    totals['pending'] += 1
            for outcome in outcomes:
                forecast = f_by_id[outcome['forecast_id']]
                for key in ('origin','target','horizon','policy_id','predicted_value'):
                    assert outcome[key] == forecast[key]
                target_tick = ticks[outcome['target']]
                state = states[outcome['target']]
                assert forecast['sequence'] < target_tick['sequence'] < outcome['sequence'] < state['sequence']
                assert outcome['actual'] == target_tick['value']
                if target_tick['value'] is None:
                    assert outcome['status'] == 'target_unavailable'
                    assert all(outcome[k] is None for k in ('actual','signed_error','absolute_error','squared_error'))
                    totals['unavailable'] += 1
                else:
                    assert outcome['status'] == 'scored'
                    error = outcome['actual'] - outcome['predicted_value']
                    assert math.isclose(outcome['absolute_error'], abs(error), abs_tol=1e-12)
                    assert math.isclose(outcome['squared_error'], error*error, abs_tol=1e-12)
                    totals['scored'] += 1
            totals['decisions'] += len(forecasts)
        assert totals['decisions'] == sum(totals[k] for k in ('scored','unavailable','pending','abstentions'))
        for h in (1,12):
            common = set.intersection(*(set(own_expert[p,h]) for p in ('persistence','arima','xgboost')))
            for policy in ('persistence','arima','xgboost'):
                row = next(r for r in metric_rows if (r['machine'],r['policy'],r['horizon'])==(machine,policy,h))
                for key, items in (('expert_matched',[own_expert[policy,h][k] for k in common]),
                                   ('complete_policy',complete[policy,h])):
                    assert row[key]['count'] == len(items)
                    if items:
                        mae = sum(o['absolute_error'] for o in items)/len(items)
                        rmse = math.sqrt(sum(o['squared_error'] for o in items)/len(items))
                        assert math.isclose(row[key]['mae'],mae,abs_tol=1e-12)
                        assert math.isclose(row[key]['rmse'],rmse,abs_tol=1e-12)
        for family, spec in config['models'][machine].items():
            for filename, sha in spec['artifact_sha256'].items():
                assert hashlib.sha256((root/spec['directory']/filename).read_bytes()).hexdigest() == sha
        result[machine] = {**totals,'shared_context_ticks':len(by_origin),'source_rows':len(inputs),
                           'selected_checkpoint_hashes_unchanged':True}
    receipt = {'passed':True, 'protected_files_verified':297, 'machines':result,
               'original_suffix_sources_reopened':False,'confirmation_access':False}
    write_new(report/'ledger_verification_extended_v1.json', receipt)
    return receipt


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-id', required=True)
    print(json.dumps(audit(parser.parse_args().run_id), indent=2))
