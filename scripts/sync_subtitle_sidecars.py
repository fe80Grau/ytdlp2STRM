import argparse
import json
import os
import re
import shutil
import sys
from pathlib import Path


DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "plugins" / "youtube" / "config.json"
EPISODE_PREFIX_RE = re.compile(r"^S\d{1,4}E\d{1,4}\s+-\s+", re.IGNORECASE)
LANG_SUFFIX_RE = re.compile(r"^[a-z]{2,3}(?:-[a-z0-9]+)?$", re.IGNORECASE)


def load_default_root():
    try:
        with open(DEFAULT_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("strm_output_folder") or "D:/media/Youtube"
    except Exception:
        return "D:/media/Youtube"


def split_subtitle_name(path):
    stem = path.stem
    parts = stem.rsplit(".", 1)
    if len(parts) == 2 and LANG_SUFFIX_RE.match(parts[1]):
        return parts[0], parts[1]
    return stem, None


def normalized_title_from_stem(stem):
    return EPISODE_PREFIX_RE.sub("", stem).strip().casefold()


def build_strm_index(directory):
    index = {}
    for strm_path in directory.glob("*.strm"):
        key = normalized_title_from_stem(strm_path.stem)
        index.setdefault(key, []).append(strm_path)
    return index


def target_for_subtitle(subtitle_path, strm_path, lang):
    if lang:
        return strm_path.with_name(f"{strm_path.stem}.{lang}{subtitle_path.suffix.lower()}")
    return strm_path.with_suffix(subtitle_path.suffix.lower())


def subtitle_already_paired(subtitle_path):
    base_stem, _lang = split_subtitle_name(subtitle_path)
    return subtitle_path.with_name(base_stem + ".strm").exists()


def iter_subtitles(root):
    for path in root.rglob("*"):
        if path.is_file() and path.suffix.lower() in (".srt", ".vtt"):
            yield path


def main():
    parser = argparse.ArgumentParser(
        description="Sync subtitle sidecar names with existing STRM names in the same folder"
    )
    parser.add_argument("--root", default=load_default_root(), help="Root folder to scan recursively")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be moved without writing files")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite target subtitle if it already exists")
    parser.add_argument("--delete-old", action="store_true", help="Deprecated: files are always moved (original is removed after move)")
    parser.add_argument("--verbose", action="store_true", help="Show skipped files")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"[ERROR] Root folder does not exist: {root}")
        sys.exit(1)

    stats = {
        "moved": 0,
        "would_move": 0,
        "already_paired": 0,
        "target_exists": 0,
        "ambiguous": 0,
        "no_match": 0,
        "errors": 0,
    }
    strm_indexes = {}

    print(f"Root: {root}")
    if args.dry_run:
        print("Mode: dry-run")
    print("-" * 60)

    for subtitle_path in iter_subtitles(root):
        try:
            if subtitle_already_paired(subtitle_path):
                stats["already_paired"] += 1
                if args.verbose:
                    print(f"[paired] {subtitle_path.relative_to(root)}")
                continue

            directory = subtitle_path.parent
            if directory not in strm_indexes:
                strm_indexes[directory] = build_strm_index(directory)

            subtitle_base, lang = split_subtitle_name(subtitle_path)
            key = normalized_title_from_stem(subtitle_base)
            matches = strm_indexes[directory].get(key, [])

            if not matches:
                stats["no_match"] += 1
                if args.verbose:
                    print(f"[no-match] {subtitle_path.relative_to(root)}")
                continue

            if len(matches) > 1:
                stats["ambiguous"] += 1
                print(f"[ambiguous] {subtitle_path.relative_to(root)} -> {len(matches)} matches")
                continue

            target_path = target_for_subtitle(subtitle_path, matches[0], lang)
            if target_path.exists() and not args.overwrite:
                stats["target_exists"] += 1
                if args.verbose:
                    print(f"[exists] {subtitle_path.relative_to(root)} -> {target_path.relative_to(root)}")
                continue

            if args.dry_run:
                stats["would_move"] += 1
                print(f"[move] {subtitle_path.relative_to(root)} -> {target_path.relative_to(root)}")
                continue

            shutil.move(str(subtitle_path), str(target_path))
            stats["moved"] += 1
            print(f"[moved] {subtitle_path.relative_to(root)} -> {target_path.relative_to(root)}")
        except Exception as e:
            stats["errors"] += 1
            print(f"[error] {subtitle_path}: {e}")

    print("-" * 60)
    print(
        "Done: "
        f"moved={stats['moved']} "
        f"would_move={stats['would_move']} "
        f"already_paired={stats['already_paired']} "
        f"target_exists={stats['target_exists']} "
        f"ambiguous={stats['ambiguous']} "
        f"no_match={stats['no_match']} "
        f"errors={stats['errors']}"
    )


if __name__ == "__main__":
    main()
