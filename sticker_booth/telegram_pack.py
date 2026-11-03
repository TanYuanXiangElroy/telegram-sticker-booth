"""Create or extend a Telegram sticker pack from sticker folders, using your own bot (stdlib only).

  python -m sticker_booth.telegram_pack --whoami                      # find your user id (after /start)
  python -m sticker_booth.telegram_pack out/me --user-id <ID> --name me_8bit --title "Me 8-Bit" [--dry-run]
  python -m sticker_booth.telegram_pack out/me ... --chat-id <ID> [--thread-id <T>]   # also post the link
  python -m sticker_booth.telegram_pack --make-topic --chat-id <GROUP_ID> --topic-name "Sticker Booth"

Each folder needs pack.json (written by sticker_booth.generate) or PNGs named after the emojis in
prompts.py (laugh.png, cry.png, ...). Token from TELEGRAM_BOT_TOKEN in .env; it is never printed.
"""
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from .env import load_env, utf8_console
from .prompts import NAMES

MAX_PER_SET, MAX_PER_CREATE = 120, 50


def _token():
    t = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not t:
        raise SystemExit("TELEGRAM_BOT_TOKEN is not set. Copy .env.example to .env and fill it in.")
    return t


def api(method, params=None, files=None):
    """Call a Bot API method. Honours 429 retry_after and sleeps ~1 s per call (rate limit)."""
    url = f"https://api.telegram.org/bot{_token()}/{method}"
    params = {k: (json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else str(v))
              for k, v in (params or {}).items() if v is not None}
    for _ in range(6):
        if files:
            b = uuid.uuid4().hex
            body = b""
            for k, v in params.items():
                body += f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
            for k, p in files.items():
                body += (f'--{b}\r\nContent-Disposition: form-data; name="{k}"; filename="{Path(p).name}"\r\n'
                         f'Content-Type: image/png\r\n\r\n').encode() + Path(p).read_bytes() + b"\r\n"
            body += f"--{b}--\r\n".encode()
            req = urllib.request.Request(url, body, {"Content-Type": f"multipart/form-data; boundary={b}"})
        else:
            req = urllib.request.Request(url, json.dumps(params).encode(), {"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                data = json.load(r)
        except urllib.error.HTTPError as e:
            data = json.load(e)
        except urllib.error.URLError as e:  # the reason never contains the token
            print(f"{method}: network error {e.reason}, retrying", file=sys.stderr)
            time.sleep(3)
            continue
        time.sleep(1)
        if data.get("ok"):
            return data["result"]
        ra = (data.get("parameters") or {}).get("retry_after")
        if data.get("error_code") == 429 and ra:
            print(f"{method}: 429, waiting {ra}s", file=sys.stderr)
            time.sleep(ra + 1)
            continue
        raise RuntimeError(f"{method} failed: {data.get('error_code')} {data.get('description')}")
    raise RuntimeError(f"{method}: gave up after retries")


def collect(folders):
    """[(png_path, emoji)] from each folder's pack.json, or from file names (laugh.png -> 😂)."""
    out = []
    for f in map(Path, folders):
        pj = f / "pack.json"
        if pj.exists():
            for s in json.loads(pj.read_text(encoding="utf-8"))["stickers"]:
                out.append((f / s["png"], s["emoji"]))
        else:
            out += [(p, NAMES[p.stem]) for p in sorted(f.glob("*.png")) if p.stem in NAMES]
    missing = [str(p) for p, _ in out if not p.exists()]
    if missing:
        raise SystemExit(f"missing files: {missing}")
    if not out:
        raise SystemExit(f"no stickers found in {folders}")
    return out


def whoami():
    """List private chats and groups that have messaged the bot. Uses getUpdates, so don't run this
    while another program polls the same token (Telegram returns 409 Conflict)."""
    users, groups = {}, {}
    for u in api("getUpdates", {"timeout": 0}):
        for key in ("message", "edited_message", "channel_post", "my_chat_member", "chat_member"):
            c = (u.get(key) or {}).get("chat", {})
            if c.get("type") == "private":
                users[c["id"]] = c.get("username") or c.get("first_name")
            elif c.get("id"):
                groups[c["id"]] = (c.get("title"), c.get("is_forum", False))
    print("Private chats (user_id, username):")
    for i, n in users.items():
        print(f"  {i}  @{n}")
    print("Groups (chat_id, title, is_forum):")
    for i, (t, fo) in groups.items():
        print(f"  {i}  {t!r}  forum={fo}")
    if not users and not groups:
        print("  (no updates: send /start to the bot, or a message in the group, then retry)")


def build_pack(folders, name, title, user_id=None, chat_id=None, thread_id=None, dry_run=False):
    """Create the set <name>_by_<bot> or append new stickers to it. Returns the t.me/addstickers link.
    dry_run works without a token (uses a placeholder bot name) and uploads nothing."""
    stickers = collect(folders)
    if len(stickers) > MAX_PER_SET:
        raise SystemExit(f"max {MAX_PER_SET} stickers per set, got {len(stickers)}")
    bot = api("getMe")["username"] if os.environ.get("TELEGRAM_BOT_TOKEN") else "<your_bot>"
    full = f"{name}_by_{bot}"
    if len(full) > 64:
        raise SystemExit(f"set name too long (max 64): {full}")
    link = f"https://t.me/addstickers/{full}"
    print(f"Set name: {full}\nTitle: {title}\nStickers ({len(stickers)}):")
    for p, e in stickers:
        print(f"  {e}  {p}")
    if dry_run:
        print(f"[dry-run] would create/extend {link}")
        return link
    if not user_id:
        raise SystemExit("--user-id is required (the pack owner; run --whoami after sending /start to the bot)")

    try:
        existing = api("getStickerSet", {"name": full})
    except RuntimeError as e:
        if "STICKERSET_INVALID" not in str(e) and "not found" not in str(e).lower():
            raise
        existing = None
    have = len(existing["stickers"]) if existing else 0
    todo = stickers[have:]  # matches by position: keep folder order stable, new stickers go last
    print(f"Set exists with {have}; adding {len(todo)}" if existing else "Creating new set")

    def inp(p, e):
        fid = api("uploadStickerFile", {"user_id": user_id, "sticker_format": "static"}, {"sticker": p})["file_id"]
        return {"sticker": fid, "format": "static", "emoji_list": [e]}

    if not existing and todo:
        api("createNewStickerSet", {"user_id": user_id, "name": full, "title": title,
                                    "sticker_type": "regular", "stickers": [inp(p, e) for p, e in todo[:MAX_PER_CREATE]]})
        todo = todo[MAX_PER_CREATE:]
    for p, e in todo:
        api("addStickerToSet", {"user_id": user_id, "name": full, "sticker": inp(p, e)})
    print(link)
    if chat_id:
        api("sendMessage", {"chat_id": chat_id, "message_thread_id": thread_id,
                            "text": f"New sticker pack: {title}\n{link}"})
        s = api("getStickerSet", {"name": full})["stickers"]
        if s:
            api("sendSticker", {"chat_id": chat_id, "message_thread_id": thread_id, "sticker": s[0]["file_id"]})
    return link


def main():
    utf8_console()
    load_env()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("folders", nargs="*", help="sticker folders, e.g. out/me")
    ap.add_argument("--whoami", action="store_true", help="list user/chat ids that messaged the bot")
    ap.add_argument("--make-topic", action="store_true", help="create a forum topic in --chat-id")
    ap.add_argument("--topic-name", default="Sticker Booth")
    ap.add_argument("--user-id", type=int, default=os.environ.get("TELEGRAM_USER_ID") or None,
                    help="pack owner's Telegram user id (or TELEGRAM_USER_ID in .env)")
    ap.add_argument("--name", help="short set name: letters, digits, underscores; starts with a letter")
    ap.add_argument("--title", help="pack title shown in Telegram")
    ap.add_argument("--chat-id", help="also post the link here (your user id for a DM, or a group id)")
    ap.add_argument("--thread-id", type=int, help="forum topic id inside --chat-id")
    ap.add_argument("--dry-run", action="store_true", help="list what would be uploaded, upload nothing")
    a = ap.parse_args()

    if a.whoami:
        return whoami()
    if a.make_topic:
        if not a.chat_id:
            sys.exit("--make-topic needs --chat-id")
        t = api("createForumTopic", {"chat_id": a.chat_id, "name": a.topic_name})
        print(f"message_thread_id={t['message_thread_id']}  name={t['name']}")
        return
    if not (a.folders and a.name and a.title):
        ap.error("need folders, --name and --title (and --user-id unless --dry-run)")
    build_pack(a.folders, a.name, a.title, a.user_id, a.chat_id, a.thread_id, a.dry_run)


if __name__ == "__main__":
    main()
