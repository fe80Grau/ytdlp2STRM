"""
Descarga los subtitulos del ultimo video (.strm) de cada canal bajo una ruta raiz.

Uso:
    python scripts/download_last_subtitles.py
    python scripts/download_last_subtitles.py --root "D:/media/Youtube" --langs es,es-orig,en,en-orig
    python scripts/download_last_subtitles.py --dry-run

Comportamiento:
 - Recorre cada subcarpeta de --root (cada canal).
 - Localiza el .strm con mayor (Season, Episode) segun nomenclatura SYYYYExx
   (fallback a mtime si no hay match).
 - Extrae el video_id del URL del .strm (ultimo segmento del path).
 - Descarga subtitulos con yt-dlp (sin descargar video) con el mismo basename.
 - Si ya existe un archivo .vtt/.srt/.ass con ese basename, salta el video.
 - Aplica un sleep configurable entre descargas para evitar HTTP 429.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
from urllib.parse import urlparse


EPISODE_RE = re.compile(r"S(\d{1,4})E(\d{1,4})", re.IGNORECASE)


DEFAULT_CONFIG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "plugins", "youtube", "config.json"
)


def load_defaults():
    root = "D:/media/Youtube"
    lang = "en"
    cookies = ""
    cookie_value = ""
    try:
        with open(DEFAULT_CONFIG, encoding="utf-8") as f:
            cfg = json.load(f)
        root = cfg.get("strm_output_folder", root)
        lang = cfg.get("lang", lang)
        cookies = cfg.get("cookies", "")
        cookie_value = cfg.get("cookie_value", "")
    except Exception:
        pass
    return root, lang, cookies, cookie_value


def find_latest_strm(channel_dir):
    """Devuelve el .strm con mayor (season, episode) segun nomenclatura SYYYYExx.

    Si ningun archivo sigue el patron, cae a seleccion por mtime.
    """
    best = None
    best_key = None
    fallback = None
    fallback_mtime = -1
    for dirpath, _dirnames, filenames in os.walk(channel_dir):
        for name in filenames:
            if not name.lower().endswith(".strm"):
                continue
            fp = os.path.join(dirpath, name)
            match = EPISODE_RE.search(name)
            if match:
                key = (int(match.group(1)), int(match.group(2)))
                if best_key is None or key > best_key:
                    best_key = key
                    best = fp
            else:
                try:
                    mtime = os.path.getmtime(fp)
                except OSError:
                    continue
                if mtime > fallback_mtime:
                    fallback_mtime = mtime
                    fallback = fp
    return best or fallback


def extract_video_id(strm_path):
    try:
        with open(strm_path, encoding="utf-8") as f:
            url = f.read().strip()
    except Exception as e:
        print(f"  [skip] No puedo leer {strm_path}: {e}")
        return None
    if not url:
        return None
    parsed = urlparse(url)
    path = parsed.path.rstrip("/")
    if not path:
        return None
    video_id = path.split("/")[-1]
    # Quitar sufijo -audio si existiera
    if video_id.endswith("-audio"):
        video_id = video_id[: -len("-audio")]
    return video_id or None


def subtitles_already_exist(strm_path):
    base_path = os.path.splitext(strm_path)[0]
    directory = os.path.dirname(base_path)
    base_name = os.path.basename(base_path)
    if not os.path.isdir(directory):
        return False
    for fname in os.listdir(directory):
        if fname.startswith(base_name + ".") and fname.endswith((".vtt", ".srt", ".ass")):
            return True
    return False


def build_command(video_id, strm_path, langs, cookies, cookie_value):
    base_path = os.path.splitext(strm_path)[0]
    command = [
        "yt-dlp",
        "--skip-download",
        "--write-subs",
        "--write-auto-subs",
        "--sub-langs", langs,
        "--sub-format", "vtt",
        "--no-warnings",
        "--ignore-errors",
        "-o", f"{base_path}.%(ext)s",
        f"https://www.youtube.com/watch?v={video_id}",
    ]
    if cookies == "cookies-from-browser" and cookie_value:
        command.extend(["--cookies-from-browser", cookie_value])
    elif cookies == "cookies" and cookie_value:
        command.extend(["--cookies", cookie_value])
    return command


def main():
    default_root, default_lang, default_cookies, default_cookie_value = load_defaults()

    parser = argparse.ArgumentParser(description="Descarga subtitulos del ultimo video de cada canal .strm")
    parser.add_argument("--root", default=default_root, help="Directorio raiz con los canales (def: %(default)s)")
    parser.add_argument(
        "--langs",
        default=f"{default_lang},{default_lang}-orig,en,en-orig",
        help="Lista de idiomas yt-dlp (def: %(default)s)",
    )
    parser.add_argument("--sleep", type=float, default=2.0, help="Segundos entre descargas (def: %(default)s)")
    parser.add_argument("--dry-run", action="store_true", help="Solo muestra lo que haria")
    parser.add_argument("--force", action="store_true", help="Descarga aunque ya existan subtitulos")
    parser.add_argument("--verbose", action="store_true", help="Muestra salida completa de yt-dlp")
    args = parser.parse_args()

    if not os.path.isdir(args.root):
        print(f"[ERROR] Directorio no existe: {args.root}")
        sys.exit(1)

    channels = sorted(
        entry for entry in os.listdir(args.root)
        if os.path.isdir(os.path.join(args.root, entry))
    )
    print(f"Raiz: {args.root}")
    print(f"Canales detectados: {len(channels)}")
    print(f"Idiomas: {args.langs}")
    print("-" * 60)

    processed = 0
    skipped = 0
    errors = 0

    for channel in channels:
        channel_dir = os.path.join(args.root, channel)
        latest = find_latest_strm(channel_dir)
        if not latest:
            print(f"[--] {channel}: sin .strm")
            continue

        video_id = extract_video_id(latest)
        if not video_id:
            print(f"[--] {channel}: no puedo extraer video_id de {latest}")
            continue

        rel = os.path.relpath(latest, args.root)
        if not args.force and subtitles_already_exist(latest):
            print(f"[skip] {rel} (subtitulos ya presentes)")
            skipped += 1
            continue

        command = build_command(video_id, latest, args.langs, default_cookies, default_cookie_value)
        print(f"[run ] {rel} -> {video_id}")

        if args.dry_run:
            print("       " + " ".join(command))
            continue

        base_path = os.path.splitext(latest)[0]
        base_name = os.path.basename(base_path)
        directory = os.path.dirname(base_path)
        before = {
            f for f in os.listdir(directory)
            if f.startswith(base_name + ".") and f.endswith((".vtt", ".srt", ".ass"))
        } if os.path.isdir(directory) else set()

        try:
            if args.verbose:
                result = subprocess.run(command, timeout=120)
                rc = result.returncode
            else:
                result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
                rc = result.returncode

            after = {
                f for f in os.listdir(directory)
                if f.startswith(base_name + ".") and f.endswith((".vtt", ".srt", ".ass"))
            } if os.path.isdir(directory) else set()
            new_files = sorted(after - before)

            if new_files:
                processed += 1
                print(f"       [ok] {len(new_files)} subs: {', '.join(f.rsplit('.', 2)[-2] for f in new_files)}")
            elif rc == 0:
                print("       [warn] yt-dlp returncode=0 pero no se crearon subtitulos (puede que no existan en esos idiomas)")
                skipped += 1
            else:
                errors += 1
                if not args.verbose:
                    err_msg = (result.stderr or result.stdout or "").strip().splitlines()
                    tail = err_msg[-1] if err_msg else f"exit {rc}"
                    print(f"       [error] {tail}")
                else:
                    print(f"       [error] exit {rc}")
        except subprocess.TimeoutExpired:
            errors += 1
            print("       [error] timeout yt-dlp")
        except Exception as e:
            errors += 1
            print(f"       [error] {e}")

        time.sleep(args.sleep)

    print("-" * 60)
    print(f"OK: {processed} | Saltados: {skipped} | Errores: {errors}")


if __name__ == "__main__":
    main()
