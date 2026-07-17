#!/usr/bin/env python3
'''Validate the byte encoding and line endings of Consumer result artifacts.'''

from __future__ import annotations

import argparse
import codecs
import os
from pathlib import Path
import subprocess
import sys
from typing import NamedTuple


EXIT_PASSED = 0
EXIT_VALIDATION_FAILURE = 1
EXIT_OPERATIONAL_ERROR = 2

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
TRACKED_RESULTS_PATHSPEC = ':(glob)results/*.md'


class ValidationTarget(NamedTuple):
    path: Path
    display_path: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Validate Consumer result artifact encoding.'
    )
    parser.add_argument(
        '--file',
        action='append',
        default=[],
        metavar='PATH',
        help='validate an explicit file instead of tracked results/*.md (repeatable)',
    )
    return parser.parse_args()


def discover_tracked_results() -> tuple[list[ValidationTarget], bool]:
    environment = os.environ.copy()
    environment['GIT_OPTIONAL_LOCKS'] = '0'
    try:
        completed = subprocess.run(
            ['git', 'ls-files', '-z', '--', TRACKED_RESULTS_PATHSPEC],
            cwd=REPOSITORY_ROOT,
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    except OSError:
        print('ERROR DISCOVERY .')
        return [], False

    if completed.returncode != 0:
        print('ERROR DISCOVERY .')
        return [], False

    try:
        relative_paths = completed.stdout.decode('utf-8', errors='strict').split('\0')
    except UnicodeDecodeError:
        print('ERROR DISCOVERY .')
        return [], False

    targets: list[ValidationTarget] = []
    for relative_path in sorted(path for path in relative_paths if path):
        candidate = (REPOSITORY_ROOT / relative_path).resolve()
        try:
            display_path = candidate.relative_to(REPOSITORY_ROOT).as_posix()
        except ValueError:
            print('ERROR DISCOVERY .')
            return [], False
        targets.append(ValidationTarget(candidate, display_path))

    if not targets:
        print('ERROR DISCOVERY .')
        return [], False
    return targets, True


def explicit_targets(values: list[str]) -> list[ValidationTarget]:
    targets = [
        ValidationTarget(Path(value).resolve(), f'external/{index:03d}')
        for index, value in enumerate(values, start=1)
    ]
    return sorted(targets, key=lambda target: target.display_path)


def validation_failure(data: bytes) -> str | None:
    if data.startswith(
        (
            codecs.BOM_UTF8,
            codecs.BOM_UTF16_LE,
            codecs.BOM_UTF16_BE,
            codecs.BOM_UTF32_LE,
            codecs.BOM_UTF32_BE,
        )
    ):
        return 'BOM'

    try:
        text = data.decode('utf-8', errors='strict')
    except UnicodeDecodeError:
        return 'UTF8'

    if '\x00' in text:
        return 'NUL'
    if '\r' in text:
        return 'CR'
    if not text.endswith('\n'):
        return 'TRAILING_LF'
    return None


def validate(targets: list[ValidationTarget]) -> int:
    validation_failed = False
    operational_error = False

    for target in targets:
        try:
            data = target.path.read_bytes()
        except OSError:
            print(f'ERROR READ {target.display_path}')
            operational_error = True
            continue

        category = validation_failure(data)
        if category is None:
            print(f'PASS ENCODING {target.display_path}')
        else:
            print(f'FAIL {category} {target.display_path}')
            validation_failed = True

    if operational_error:
        return EXIT_OPERATIONAL_ERROR
    if validation_failed:
        return EXIT_VALIDATION_FAILURE
    return EXIT_PASSED


def main() -> int:
    arguments = parse_args()
    if arguments.file:
        targets = explicit_targets(arguments.file)
    else:
        targets, discovery_succeeded = discover_tracked_results()
        if not discovery_succeeded:
            return EXIT_OPERATIONAL_ERROR
    return validate(targets)


if __name__ == '__main__':
    sys.exit(main())
