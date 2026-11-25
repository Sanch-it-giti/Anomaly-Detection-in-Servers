import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

spec = importlib.util.spec_from_file_location('adapter',Path(__file__).resolve().parents[1]/'scripts/build_evidence.py')
adapter = importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)


class EvidenceTests(unittest.TestCase):
    def test_real_report_schemas(self):
        with TemporaryDirectory() as temp:
            data=adapter.build(output=Path(temp))
            self.assertEqual(len(data['artifacts']),len(adapter.ALLOWLIST))
            self.assertTrue(data['readOnly'])

    def test_missing_sources_do_not_fabricate_rows(self):
        with TemporaryDirectory() as root,TemporaryDirectory() as output:
            data=adapter.build(Path(root),Path(output))
            self.assertTrue(all(a['status']=='unavailable' and 'rows' not in a for a in data['artifacts']))

    def test_coverage_must_match_genuine_denominator(self):
        path=adapter.ROOT/adapter.ALLOWLIST['intervals-b'][0]
        rows=adapter.parse_csv(path.read_bytes());rows[0]['empirical_coverage_available_only']=1
        with self.assertRaises(ValueError):adapter.validate_rows('intervals-b',rows)

    def test_nonfinite_rejected(self):
        with self.assertRaises(ValueError):adapter.parse_csv(b'mae\nnan\n')

    def test_duplicate_comparison_rejected(self):
        rows=adapter.parse_csv((adapter.ROOT/adapter.ALLOWLIST['macro'][0]).read_bytes())
        with self.assertRaises(ValueError):adapter.validate_rows('macro',rows+[rows[0]])

    def test_no_private_data_sources(self):
        for path,_ in adapter.ALLOWLIST.values():
            self.assertTrue(path.startswith(('reports/','configs/')))
            self.assertNotIn('.jsonl',path);self.assertNotIn('.key',path)

    def test_false_qualification_count_rejected(self):
        import json
        data=json.loads((adapter.ROOT/adapter.ALLOWLIST['qualification'][0]).read_text())
        data['full_v2_qualified_count']=6
        with self.assertRaises(ValueError):adapter.validate_json('qualification',data)

    def test_confirmation_execution_config_rejected(self):
        with self.assertRaises(ValueError):adapter.validate_json('selector-rules',{'confirmation_execution_allowed':True})

if __name__=='__main__':unittest.main()
