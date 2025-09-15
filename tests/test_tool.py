import contextlib
import copy
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from gcp_quota_headroom.core import analyze
from gcp_quota_headroom.cli import main

EXAMPLE = Path(__file__).resolve().parents[1] / 'examples' / 'input.json'


def example():
    return json.loads(EXAMPLE.read_text())


class CliTests(unittest.TestCase):
    def run_cli(self, args, stdin=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err), patch('sys.stdin', io.StringIO(stdin or '')):
            code = main(args)
        return code, out.getvalue(), err.getvalue()

    def test_sample_json_matches_core(self):
        code, out, err = self.run_cli([str(EXAMPLE), '--json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), analyze(example()))
        self.assertEqual(err, '')

    def test_stdin_and_ci_exit_code(self):
        code, out, _ = self.run_cli(['-', '--json', '--fail-on-findings'], json.dumps(example()))
        self.assertEqual(code, 1)
        self.assertTrue(json.loads(out)['attention_required'])

    def test_malformed_json_does_not_echo_contents(self):
        code, out, err = self.run_cli(['-'], '{fictional-private-value')
        self.assertEqual(code, 2)
        self.assertEqual(out, '')
        self.assertNotIn('fictional-private-value', err)

    def test_wrong_shape_is_input_error(self):
        for value in (None, 'wrong', 12, {'bad': True}):
            with self.subTest(value=value):
                code, _, _ = self.run_cli(['-'], json.dumps(value))
                self.assertEqual(code, 2)

    def test_missing_file_is_input_error(self):
        code, _, _ = self.run_cli(['/nonexistent/example-fixture.json'])
        self.assertEqual(code, 2)

    def test_text_report(self):
        code, out, _ = self.run_cli([str(EXAMPLE)])
        self.assertEqual(code, 0)
        self.assertIn('Attention required', out)

    def test_core_does_not_mutate_input(self):
        data = example()
        original = copy.deepcopy(data)
        analyze(data)
        self.assertEqual(data, original)


class QuotaTests(unittest.TestCase):
    def row(self, usage=80, limit=100):
        return {'name': 'example-region', 'quotas': [{'metric': 'CPUS', 'usage': usage, 'limit': limit}]}

    def test_threshold_and_ranking(self):
        report = analyze(example())
        self.assertEqual([f['severity'] for f in report['findings']], ['critical', 'warning', 'ok'])
        self.assertEqual(report['findings'][1]['remaining'], 14)
        self.assertEqual(analyze(self.row(79.9))['findings'][0]['severity'], 'ok')
        self.assertEqual(analyze(self.row())['findings'][0]['severity'], 'warning')

    def test_zero_limit_and_over_limit(self):
        zero = analyze(self.row(0, 0))['findings'][0]
        self.assertEqual(zero['severity'], 'critical')
        self.assertIsNone(zero['used_percent'])
        over = analyze(self.row(101, 100))['findings'][0]
        self.assertEqual(over['remaining'], 0)
        self.assertEqual(over['over_limit'], 1)

    def test_reject_invalid_numbers(self):
        for value in (-1, float('nan'), float('inf'), True, '10', None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                analyze(self.row(value))

    def test_rest_list_and_empty_report(self):
        self.assertEqual(analyze({'items': [self.row()]})['resources_checked'], 1)
        self.assertEqual(analyze([])['quotas_checked'], 0)
        self.assertFalse(analyze([])['attention_required'])

    def test_duplicate_metric_rejected(self):
        data = self.row()
        data['quotas'] *= 2
        with self.assertRaises(ValueError):
            analyze(data)

    def test_distinct_scopes_same_metric(self):
        other = self.row()
        other['name'] = 'other-region'
        self.assertEqual(analyze([self.row(), other])['quotas_checked'], 2)

    def test_missing_quotas_not_silent_success(self):
        with self.assertRaises(ValueError):
            analyze({'name': 'example-region'})

    def test_incomplete_pagination_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze({'items': [], 'nextPageToken': 'example-next-page'})


if __name__ == "__main__":
    unittest.main()
