import argparse
import json
import os
import re
import sys


DEFAULT_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "plugins", "youtube", "config.json"
)


def load_default_root():
    try:
        with open(DEFAULT_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("strm_output_folder") or "D:/media/Youtube"
    except Exception:
        return "D:/media/Youtube"


def clean_vtt_text_line(line):
    line = re.sub(r'<\d{2}:\d{2}:\d{2}\.\d{3}>', '', line)
    line = re.sub(r'</?c[._\w]*>', '', line)
    return line


def fix_vtt_cue_timing_line(line):
    line = re.sub(r'\s+position:\d+(\.\d+)?%', '', line)
    line = re.sub(r'\s+line:\d+(\.\d+)?%', '', line)
    line = re.sub(r'\s+line:\d+', '', line)
    if re.search(r'\balign:(start|left)\b', line):
        line = re.sub(r'\balign:(start|left)\b', 'align:middle', line)
    elif not re.search(r'\balign:\w+\b', line):
        line += ' align:middle'
    return line


def fix_vtt_alignment(vtt_text):
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
        for i, line in enumerate(block_lines):
            if '-->' in line:
                timing_idx = i
                break

        if timing_idx is None:
            out_blocks.append(block)
            continue

        timing_line = fix_vtt_cue_timing_line(block_lines[timing_idx])
        text_lines = [clean_vtt_text_line(line) for line in block_lines[timing_idx + 1:]]
        non_empty = [line for line in text_lines if line.strip()]
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


def vtt_timestamp_to_srt(timestamp):
    return timestamp.strip().replace('.', ',')


def vtt_text_to_srt(vtt_text):
    blocks = re.split(r'\r?\n\r?\n', vtt_text)
    srt_blocks = []
    cue_number = 1

    for block in blocks:
        lines = [line.strip('\ufeff') for line in block.splitlines()]
        if not lines:
            continue

        timing_idx = None
        for idx, line in enumerate(lines):
            if '-->' in line:
                timing_idx = idx
                break

        if timing_idx is None:
            continue

        timing_parts = lines[timing_idx].split('-->')
        if len(timing_parts) != 2:
            continue

        start_time = vtt_timestamp_to_srt(timing_parts[0])
        end_time = vtt_timestamp_to_srt(timing_parts[1].split()[0])
        text_lines = [clean_vtt_text_line(line) for line in lines[timing_idx + 1:] if line.strip()]
        text_lines = [re.sub(r'<[^>]+>', '', line).strip() for line in text_lines]
        text_lines = [line for line in text_lines if line]
        if not text_lines:
            continue

        srt_blocks.append(f"{cue_number}\n{start_time} --> {end_time}\n" + "\n".join(text_lines))
        cue_number += 1

    return "\n\n".join(srt_blocks) + ("\n" if srt_blocks else "")


def iter_vtt_files(root):
    for dirpath, _dirnames, filenames in os.walk(root):
        for filename in filenames:
            if filename.lower().endswith('.vtt'):
                yield os.path.join(dirpath, filename)


def convert_file(vtt_path, overwrite=False, delete_vtt=False, dry_run=False):
    srt_path = os.path.splitext(vtt_path)[0] + '.srt'
    if os.path.exists(srt_path) and not overwrite:
        return 'skipped', srt_path

    if dry_run:
        return 'would_convert', srt_path

    with open(vtt_path, 'r', encoding='utf-8') as f:
        vtt_text = f.read()

    srt_text = vtt_text_to_srt(fix_vtt_alignment(vtt_text))
    if not srt_text:
        return 'empty', srt_path

    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_text)

    if delete_vtt:
        os.remove(vtt_path)

    return 'converted', srt_path


def main():
    parser = argparse.ArgumentParser(description='Convert existing WebVTT subtitles to SRT sidecar files')
    parser.add_argument('--root', default=load_default_root(), help='Root folder to scan recursively')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be converted without writing files')
    parser.add_argument('--overwrite', action='store_true', help='Overwrite existing .srt files')
    parser.add_argument('--delete-vtt', action='store_true', help='Delete .vtt files after successful conversion')
    parser.add_argument('--verbose', action='store_true', help='Show skipped and empty files')
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print(f"[ERROR] Root folder does not exist: {args.root}")
        sys.exit(1)

    stats = {
        'converted': 0,
        'would_convert': 0,
        'skipped': 0,
        'empty': 0,
        'errors': 0,
    }

    print(f"Root: {args.root}")
    if args.dry_run:
        print("Mode: dry-run")
    if args.delete_vtt:
        print("Mode: delete-vtt enabled")
    print('-' * 60)

    for vtt_path in iter_vtt_files(args.root):
        try:
            status, srt_path = convert_file(
                vtt_path,
                overwrite=args.overwrite,
                delete_vtt=args.delete_vtt,
                dry_run=args.dry_run,
            )
            stats[status] += 1
            if status in ('converted', 'would_convert') or args.verbose:
                rel_vtt = os.path.relpath(vtt_path, args.root)
                rel_srt = os.path.relpath(srt_path, args.root)
                print(f"[{status}] {rel_vtt} -> {rel_srt}")
        except Exception as e:
            stats['errors'] += 1
            rel_vtt = os.path.relpath(vtt_path, args.root)
            print(f"[error] {rel_vtt}: {e}")

    print('-' * 60)
    print(
        "Done: "
        f"converted={stats['converted']} "
        f"would_convert={stats['would_convert']} "
        f"skipped={stats['skipped']} "
        f"empty={stats['empty']} "
        f"errors={stats['errors']}"
    )


if __name__ == '__main__':
    main()
