#!/usr/bin/env python3
"""Check file-bound qualification evidence before a public alpha release.

This checks evidence completeness and hashes, not whether a human's test claim
is truthful. Keep original logs/screenshots and review them before publishing.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def evaluate(policy, report, evidence_root, image=None):
    errors = []
    if report.get('version') != policy['version']:
        errors.append('release version mismatch')
    if image is None or not image.is_file():
        errors.append('ISO file is required')
    elif report.get('iso_sha256') != sha256(image):
        errors.append('report does not match this ISO')
    if not report.get('source_commit'):
        errors.append('source commit missing')
    checks = report.get('checks', [])
    if not isinstance(checks, list):
        return errors + ['checks must be a list']
    ids = [check.get('id') for check in checks if isinstance(check, dict)]
    if len(ids) != len(set(ids)):
        errors.append('duplicate test IDs')
    by_id = {check['id']: check for check in checks if isinstance(check, dict) and 'id' in check}
    for name in policy['required_checks']:
        check = by_id.get(name, {})
        if check.get('status') != 'pass':
            errors.append(name + ': not passed')
            continue
        evidence = check.get('evidence', [])
        if not isinstance(evidence, list) or not evidence:
            errors.append(name + ': evidence missing')
            continue
        for item in evidence:
            if not isinstance(item, dict) or not isinstance(item.get('path'), str):
                errors.append(name + ': malformed evidence'); continue
            path = (evidence_root / item['path']).resolve()
            if not path.is_relative_to(evidence_root.resolve()) or not path.is_file():
                errors.append(name + ': evidence file missing or outside report directory')
            elif sha256(path) != item.get('sha256'):
                errors.append(name + ': evidence hash mismatch')
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', type=Path, default=ROOT / 'iso/release/alpha.json')
    parser.add_argument('--report', type=Path)
    parser.add_argument('--iso', type=Path)
    args = parser.parse_args()
    policy = json.loads(args.policy.read_text())
    if args.report is None:
        print('NOT READY: no ISO qualification report. Required checks:')
        print('\n'.join('  pending: ' + name for name in policy['required_checks']))
        return 1
    errors = evaluate(policy, json.loads(args.report.read_text()), args.report.resolve().parent, args.iso)
    if errors:
        print('NOT READY:\n' + '\n'.join('  ' + error for error in errors))
        return 1
    print('Evidence completeness passed. Review original evidence and known issues before publishing.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
