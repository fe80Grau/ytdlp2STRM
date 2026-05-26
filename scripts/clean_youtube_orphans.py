"""
Clean orphan YouTube companion files (.nfo, .png, .jpg, .vtt, .srt, .ass)
left over when title changes / episode counter incremented but no .strm
was actually written.

A file is considered an ORPHAN when its basename (without extension and
without trailing language suffixes like .es / .es-orig) does NOT match
any existing .strm file in the same directory.

Usage:
    # Dry-run (default): only lists what would be deleted
    python scripts/clean_youtube_orphans.py "D:/media/Youtube"

    # Actually delete
    python scripts/clean_youtube_orphans.py "D:/media/Youtube" --delete

    # Restrict to a single channel/season folder
    python scripts/clean_youtube_orphans.py "D:/media/Youtube/@Channel [ID]/Season 2026" --delete
"""

import argparse
import os
import re
import sys

# Extensions that are considered "companion" files of a .strm
COMPANION_EXTS = {
    '.nfo',
    '.png', '.jpg', '.jpeg', '.webp',
    '.vtt', '.srt', '.ass',
}

# Language / variant suffixes that may appear between the basename and the
# extension, e.g. "Title.es.vtt", "Title.es-orig.srt", "Title.en-US.vtt".
LANG_SUFFIX_RE = re.compile(r'\.[A-Za-z]{2,3}(?:-[A-Za-z0-9]+)?$')


def strip_companion_suffixes(filename_no_ext):
    """Remove language suffixes so 'Title.es-orig' -> 'Title'."""
    base = filename_no_ext
    # Strip up to 2 language-like suffixes (e.g. ".es-orig" then nothing).
    for _ in range(2):
        m = LANG_SUFFIX_RE.search(base)
        if not m:
            break
        base = base[:m.start()]
    return base


def collect_strm_bases(directory):
    """Return the set of strm basenames (without extension) in a directory."""
    bases = set()
    try:
        for entry in os.listdir(directory):
            full = os.path.join(directory, entry)
            if os.path.isfile(full) and entry.lower().endswith('.strm'):
                bases.add(os.path.splitext(entry)[0])
    except OSError:
        pass
    return bases


def find_orphans(root):
    """Yield absolute paths of orphan companion files under root."""
    for dirpath, _dirs, files in os.walk(root):
        strm_bases = collect_strm_bases(dirpath)
        for name in files:
            stem, ext = os.path.splitext(name)
            ext_lower = ext.lower()
            if ext_lower not in COMPANION_EXTS:
                continue
            # Reduce 'Title.es-orig' / 'Title.en' to 'Title' for matching.
            candidate_base = strip_companion_suffixes(stem)
            if candidate_base in strm_bases or stem in strm_bases:
                continue
            yield os.path.join(dirpath, name)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('path', help='Root folder to scan (e.g. D:/media/Youtube)')
    parser.add_argument('--delete', action='store_true', help='Actually delete the orphan files. Without this flag, runs in dry-run mode.')
    parser.add_argument('--quiet', action='store_true', help='Only print summary, not each file.')
    args = parser.parse_args()

    root = os.path.abspath(args.path)
    if not os.path.isdir(root):
        print(f'ERROR: not a directory: {root}', file=sys.stderr)
        sys.exit(1)

    mode = 'DELETE' if args.delete else 'DRY-RUN'
    print(f'[{mode}] Scanning: {root}')
    print(f'Companion extensions: {sorted(COMPANION_EXTS)}')
    print('-' * 60)

    total = 0
    deleted = 0
    errors = 0
    for orphan in find_orphans(root):
        total += 1
        if not args.quiet:
            print(('DELETE ' if args.delete else 'ORPHAN ') + orphan)
        if args.delete:
            try:
                os.remove(orphan)
                deleted += 1
            except OSError as e:
                errors += 1
                print(f'  ! could not delete: {e}', file=sys.stderr)

    print('-' * 60)
    print(f'Orphans found: {total}')
    if args.delete:
        print(f'Deleted: {deleted}')
        if errors:
            print(f'Errors: {errors}')
    else:
        print('Run again with --delete to actually remove them.')


if __name__ == '__main__':
    main()
