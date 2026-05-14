#!/usr/bin/env python3
"""
Fix alignment of all downloaded VTT subtitles.

Scans the strm_path directory recursively for .vtt files, removes horizontal
position offsets (position:...%) and forces center alignment (align:middle)
to ensure subtitles display correctly in Emby/Jellyfin.

Usage:
    python scripts/fix_all_subtitles_alignment.py [--dry-run] [--verbose]
"""

import os
import re
import sys
import argparse

# Get strm_path from ytdlp2STRM config
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from clases.config import config
    STRM_PATH = config.STRM_PATH
except Exception:
    STRM_PATH = os.environ.get('STRM_PATH', '/media/youtube')


def _clean_vtt_text_line(line):
    line = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', line)
    line = re.sub(r'</?c[._\w]*>', '', line)
    return line


def _fix_vtt_cue_timing_line(line):
    line = re.sub(r'\s+position:\d+(\.\d+)?%', '', line)
    line = re.sub(r'\s+line:\d+(\.\d+)?%', '', line)
    line = re.sub(r'\s+line:\d+', '', line)
    if re.search(r'\balign:(start|left)\b', line):
        line = re.sub(r'\balign:(start|left)\b', 'align:middle', line)
    elif not re.search(r'\balign:\w+\b', line):
        line += ' align:middle'
    return line


def fix_vtt_alignment(vtt_text):
    """
    Post-process a WebVTT string for Emby/Jellyfin compatibility.

    Centers cues and removes the rollup/persiana effect by collapsing
    each cue to only its newest text line and dropping duplicate
    transition cues emitted by YouTube.
    """
    parts = re.split(r'\r?\n\r?\n', vtt_text)
    if not parts:
        return vtt_text

    header = parts[0]
    cue_blocks = parts[1:]

    out_blocks = [header]
    last_text = None

    for block in cue_blocks:
        block_lines = block.splitlines()
        if not block_lines:
            continue

        timing_idx = None
        for i, ln in enumerate(block_lines):
            if '-->' in ln:
                timing_idx = i
                break
        if timing_idx is None:
            out_blocks.append(block)
            continue

        timing_line = _fix_vtt_cue_timing_line(block_lines[timing_idx])
        text_lines = [_clean_vtt_text_line(l) for l in block_lines[timing_idx + 1:]]

        non_empty = [l for l in text_lines if l.strip()]
        if not non_empty:
            continue

        new_text = non_empty[-1].rstrip()

        if new_text == last_text:
            continue
        last_text = new_text

        cue = []
        cue.extend(block_lines[:timing_idx])
        cue.append(timing_line)
        cue.append(new_text)
        out_blocks.append('\n'.join(cue))

    return '\n\n'.join(out_blocks)


def process_vtt_file(file_path, dry_run=False, verbose=False):
    """Process a single VTT file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            original = f.read()

        fixed = fix_vtt_alignment(original)

        if original == fixed:
            if verbose:
                print(f"  [SKIP] {file_path}")
            return False

        if dry_run:
            print(f"  [DRY-RUN] Would fix: {file_path}")
            return True

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(fixed)

        print(f"  [FIXED] {file_path}")
        return True

    except Exception as e:
        print(f"  [ERROR] {file_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Fix alignment of all downloaded VTT subtitles for Emby/Jellyfin'
    )
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Show what would be done without modifying files'
    )
    parser.add_argument(
        '--verbose', '-v', action='store_true',
        help='Show detailed output including skipped files'
    )
    parser.add_argument(
        '--path', default=STRM_PATH,
        help=f'Path to scan for VTT files (default: {STRM_PATH})'
    )
    args = parser.parse_args()

    print(f"Scanning for .vtt files in: {args.path}")
    if args.dry_run:
        print("Mode: DRY RUN (no changes will be made)")

    fixed_count = 0
    skipped_count = 0
    error_count = 0

    for root, dirs, files in os.walk(args.path):
        for filename in files:
            if filename.endswith('.vtt'):
                file_path = os.path.join(root, filename)
                result = process_vtt_file(
                    file_path,
                    dry_run=args.dry_run,
                    verbose=args.verbose
                )
                if result:
                    fixed_count += 1
                else:
                    skipped_count += 1

    print(f"\nDone: {fixed_count} fixed, {skipped_count} skipped, {error_count} errors")


if __name__ == '__main__':
    main()
