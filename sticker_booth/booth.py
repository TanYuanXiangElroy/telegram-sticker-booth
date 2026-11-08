"""Sticker booth: a numbered prompt menu -> previews -> approve the ones you like -> 512px stickers -> your Telegram pack.

  python -m sticker_booth.booth                         # interactive: type the commands below at the booth> prompt
  python -m sticker_booth.booth photo selfie.jpg [--extra "..."|--extra CLEAN_SHAVEN] [--style pixel]
  python -m sticker_booth.booth list                    # numbered menu (built-in packs, then your own)
  python -m sticker_booth.booth add [--name duck --emoji 🦆 --scene "The person in the photo ..."]
  python -m sticker_booth.booth run 10 11 [--yes] [--variations] [--seed N]
  python -m sticker_booth.booth approve 11 [--pack NAME] [--yes|--no-upload]
  python -m sticker_booth.booth status

Global options go before the command: --session NAME (default "me"), --dry-run (no API calls: fake previews
from examples/, no Telegram writes). Files live in sessions/<NAME>/ (git-ignored); your prompts in my_prompts.json.
Optional --variations / --seed on run: vary pose/expression/props/text; seed reproduces prompt choices only.
"""
import argparse
import json
import os
import re
import shlex
import shutil
from pathlib import Path


from . import generate, postprocess, prompts, telegram_pack
from .env import REPO_ROOT, load_env, utf8_console

MY_PROMPTS = REPO_ROOT / "my_prompts.json"
SESSIONS = REPO_ROOT / "sessions"
EXAMPLES = REPO_ROOT / "examples"
DEFAULT_PALETTE = "bright, cheerful accent colours"


# ---------- prompt menu ----------
def load_mine():
    return json.loads(MY_PROMPTS.read_text(encoding="utf-8")) if MY_PROMPTS.exists() else []


def menu():
    """[{num, group, name, emoji, scene, prompt(style, extra)}] in stable order: built-in packs, then mine."""
    items = []
    for group, keys in prompts.PACKS.items():
        for e in keys:
            name, scene = prompts.EMOJIS[e][:2]
            items.append(dict(group=group, name=name, emoji=e, scene=scene,
                              prompt=lambda style, extra, e=e, variations=False, seed=None:
                              prompts.build_prompt(e, style, extra, variations=variations, seed=seed)))
    for m in load_mine():
        def own(style, extra, m=m, variations=False, seed=None):
            p = prompts.TEMPLATE.format(scene=m["scene"], style=prompts.STYLES[style],
                                        palette=m.get("palette") or DEFAULT_PALETTE)
            parts = [p, m.get("notes", ""), prompts.NO_PANEL, extra]
            if variations:
                if seed is None:
                    raise ValueError("variations=True requires a seed")
                parts.append(prompts.variation_extra_by_name(m["name"], seed))
            return " ".join(x for x in parts if x).strip()
        items.append(dict(group="mine", name=m["name"], emoji=m["emoji"], scene=m["scene"], prompt=own))
    for i, it in enumerate(items, 1):
        it["num"] = i
    return items


def short(scene, n=64):
    s = re.sub(r"^(Just the head of )?the person in the photo,? ", "", scene, flags=re.I)
    return s if len(s) <= n else s[:n - 1].rstrip() + "…"


def select(specs, items):
    """'10', 'dragon', 'dev', 'mine', 'all' -> menu items (in the order given, no duplicates)."""
    out, bad = [], []
    for s in specs:
        s = s.strip().strip(",")
        if s == "all":
            hits = items
        elif s.isdigit():
            hits = [it for it in items if it["num"] == int(s)]
        else:
            hits = [it for it in items if it["group"] == s] or [it for it in items if s in (it["name"], it["emoji"])]
        (out.extend(h for h in hits if h not in out) if hits else bad.append(s))
    if bad:
        raise SystemExit(f"Not on the menu: {', '.join(bad)} (see: list)")
    return out


# ---------- session ----------
class Session:
    def __init__(self, name):
        self.dir = SESSIONS / name
        self.file = self.dir / "session.json"
        self.data = json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else {
            "photo": None, "extra": "", "style": "pixel", "previews": {}, "approved": {}, "pack": None, "uploaded": {}}

    def save(self):
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file.write_text(json.dumps(self.data, ensure_ascii=False, indent=2), encoding="utf-8")


def ask(q, default=False, auto=None):
    """y/N question. auto=True/False answers it without reading stdin (--yes / --no-upload)."""
    if auto is not None:
        print(f"{q} {'y' if auto else 'N'}  (auto)")
        return auto
    try:
        a = input(f"{q} ").strip().lower()
    except EOFError:
        a = ""
    return a in ("y", "yes") if a else default


def expand_extra(text):
    """'CLEAN_SHAVEN,COLOURS_BLACK_HAIR_LIGHT_SKIN' -> those prompts.py sentences; anything else is used as is."""
    parts = [p.strip() for p in text.split(",")]
    if text and all(re.fullmatch(r"[A-Z][A-Z0-9_]+", p) and isinstance(getattr(prompts, p, None), str) for p in parts):
        return " ".join(getattr(prompts, p) for p in parts)
    return text


# ---------- commands ----------
def cmd_photo(s, a):
    src = Path(a.path)
    if not src.is_file():
        raise SystemExit(f"no such photo: {src}")
    s.dir.mkdir(parents=True, exist_ok=True)
    dst = s.dir / f"photo{src.suffix.lower()}"
    shutil.copyfile(src, dst)
    s.data.update(photo=dst.name, style=a.style or s.data["style"])
    if a.extra is not None:
        s.data["extra"] = expand_extra(a.extra)
    s.save()
    print(f"Photo saved: {dst}\nStyle: {s.data['style']}\nExtra likeness text: {s.data['extra'] or '(none)'}")


def cmd_list(s, a):
    group = None
    for it in menu():
        if it["group"] != group:
            group = it["group"]
            print(f"\n{group}")
        print(f"  {it['num']:>3}  {it['emoji']}  {it['name']:<14} {short(it['scene'])}")
    if not load_mine():
        print("\nmine\n       (none yet: 'add' your own prompt)")


def cmd_add(s, a):
    def get(v, q, required=True):
        while not v:
            v = input(f"{q}: ").strip()
            if not required:
                break
        return v
    name = get(a.name, "Short name (letters, digits, _)").lower()
    if not re.fullmatch(r"[a-z][a-z0-9_]{0,30}", name):
        raise SystemExit("name: start with a letter; letters, digits and _ only")
    if any(it["name"] == name for it in menu()):
        raise SystemExit(f"'{name}' is already on the menu")
    emoji = get(a.emoji, "Emoji for Telegram (one emoji)")
    scene = get(a.scene, "Scene and pose, e.g. 'The person in the photo riding a duck'")
    palette = a.palette if a.palette is not None else get(None, f"Props palette [{DEFAULT_PALETTE}]", required=False)
    mine = load_mine() + [{"name": name, "emoji": emoji, "scene": scene, "palette": palette or ""}]
    MY_PROMPTS.write_text(json.dumps(mine, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Added #{menu()[-1]['num']} {emoji} {name} to 'mine' ({MY_PROMPTS.name})")


def fake_raw(name):
    p = EXAMPLES / "gemini_raw" / f"{name}.png"
    return p if p.exists() else EXAMPLES / "sample_raw.png"


def cmd_run(s, a, dry):
    if not s.data["photo"]:
        raise SystemExit("set a photo first: photo <path>")
    seed = generate.resolve_variation_seed(a.variations, a.seed)
    todo = select(a.items, menu())
    prev = s.dir / "previews"
    prev.mkdir(parents=True, exist_ok=True)
    fresh = [it for it in todo if a.again or not (prev / f"{it['num']}_{it['name']}.png").exists()]
    cost = len(fresh) * generate.COST_PER_IMAGE
    names = ", ".join(f"{it['num']} {it['name']}" for it in todo)
    print(f"{len(todo)} prompt(s): {names}")
    print(f"{len(fresh)} new image(s) to generate, about ${cost:.2f} (at ${generate.COST_PER_IMAGE}/image)"
          + ("  [dry run: no API calls]" if dry else ""))
    if fresh and not dry and not os.environ.get("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY is not set (put it in .env), or add --dry-run to test the flow for free.")
    if fresh and not ask("Go ahead? [y/N]", auto=True if a.yes else None):
        return print("Cancelled.")
    jpeg = generate.photo_jpeg(s.dir / s.data["photo"])
    for it in todo:
        raw = prev / f"{it['num']}_{it['name']}.png"
        if it in fresh:
            try:
                if dry:
                    shutil.copyfile(fake_raw(it["name"]), raw)
                else:
                    prompt = it["prompt"](s.data["style"], s.data["extra"],
                                          variations=seed is not None, seed=seed)
                    raw.write_bytes(generate.gemini(jpeg, prompt))
            except generate.StopRun as e:
                raise SystemExit(f"Stopped: {e}")
            except Exception as e:
                print(f"  x {it['num']} {it['name']}: {e}")
                continue
        s.data["previews"][str(it["num"])] = {"name": it["name"], "emoji": it["emoji"], "raw": f"previews/{raw.name}"}
        print(f"  ok {it['num']} {it['emoji']} {it['name']} -> {raw}")
    s.save()
    sheet = preview_sheet(s, [str(it["num"]) for it in todo])
    print(f"Preview sheet: {sheet}\nKeep the ones you like with: approve <numbers>")


def preview_sheet(s, nums):
    items = [(f"{n} {s.data['previews'][n]['name']}", postprocess.process(s.dir / s.data["previews"][n]["raw"]))
             for n in nums if n in s.data["previews"]]
    path = s.dir / "previews" / "sheet.png"
    if items:
        postprocess.contact_sheet(items, path, cols=4)
    return path


def cmd_approve(s, a, dry):
    picked = []
    for n in a.nums:
        n = n.strip(",")
        if n not in s.data["previews"]:
            raise SystemExit(f"#{n} has no preview yet (run {n} first)")
        p = s.data["previews"][n]
        base = s.dir / "approved" / f"{n}_{p['name']}"
        postprocess.save_sticker(postprocess.process(s.dir / p["raw"]), base)
        s.data["approved"][n] = {"name": p["name"], "emoji": p["emoji"], "png": f"approved/{base.name}.png"}
        picked.append(n)
        print(f"  sticker {n} {p['emoji']} {p['name']} -> {base}.png / .webp")
    s.save()
    offer_pack(s, picked, a, dry)


# ---------- Telegram ----------
def offer_pack(s, nums, a, dry):
    """Add approved stickers to a pack this bot made, or offer to create one. A bot can only edit its own packs."""
    if not os.environ.get("TELEGRAM_BOT_TOKEN"):
        return print(f"Telegram not set up (TELEGRAM_BOT_TOKEN in .env); stickers are in {s.dir / 'approved'}.")
    auto = True if a.yes else False if (a.no_upload or dry) else None
    user = int(os.environ.get("TELEGRAM_USER_ID") or 0)  # only needed to upload; looking up a pack works without it
    bot = telegram_pack.api("getMe")["username"]
    suffix = f"_by_{bot}"
    name = a.pack or s.data.get("pack")
    pack = None
    if name and not name.lower().endswith(suffix.lower()):
        print(f"'{name}' was not made by this bot (@{bot}). Telegram only lets a bot add stickers to packs it "
              f"created itself, whose name ends in '{suffix}'. Add them in @Stickers by hand, or make a new pack below.")
        name = None
    if name:
        try:
            pack = telegram_pack.api("getStickerSet", {"name": name})
        except RuntimeError as e:
            if "STICKERSET_INVALID" not in str(e) and "not found" not in str(e).lower():
                raise
            print(f"Pack {name} does not exist (yet).")
    done = set(s.data["uploaded"].get(name or "", []))
    todo = [n for n in nums if n not in done]
    if not todo:
        return print("Nothing new to upload.")
    if pack:
        s.data["pack"] = name
        s.save()
        print(f"Found your pack: {pack['title']} ({len(pack['stickers'])} stickers) https://t.me/addstickers/{name}")
        if not ask(f"Add these {len(todo)} sticker(s) to {pack['title']}? [y/N]", auto=auto):
            return print(f"Not uploaded; stickers are in {s.dir / 'approved'}.")
        need_user(user)
        for n in todo:
            telegram_pack.api("addStickerToSet", {"user_id": user, "name": name, "sticker": upload(s, n, user)})
            s.data["uploaded"].setdefault(name, []).append(n)
            s.save()
        return print(f"Added. https://t.me/addstickers/{name}")
    short_name = re.sub(r"\W", "_", f"booth_{s.dir.name}").lower()
    new = f"{short_name}{suffix}"
    if not ask(f"Create a new pack {new} with these {len(todo)} sticker(s)? [y/N]", auto=auto):
        return print(f"Not uploaded; stickers are in {s.dir / 'approved'}.")
    need_user(user)
    telegram_pack.api("createNewStickerSet", {"user_id": user, "name": new, "title": f"{s.dir.name} booth",
                                              "sticker_type": "regular", "stickers": [upload(s, n, user) for n in todo]})
    s.data["pack"] = new
    s.data["uploaded"][new] = list(todo)
    s.save()
    print(f"Created https://t.me/addstickers/{new}")


def need_user(user):
    if not user:
        raise SystemExit("Set TELEGRAM_USER_ID in .env (your numeric id; python -m sticker_booth.telegram_pack --whoami).")


def upload(s, n, user):
    st = s.data["approved"][n]
    fid = telegram_pack.api("uploadStickerFile", {"user_id": user, "sticker_format": "static"},
                            {"sticker": s.dir / st["png"]})["file_id"]
    return {"sticker": fid, "format": "static", "emoji_list": [st["emoji"]]}


def cmd_status(s, a):
    d = s.data
    print(f"Session: {s.dir}\nPhoto: {d['photo'] or '(none: photo <path>)'}  style {d['style']}")
    print(f"Extra: {(d['extra'][:90] + '…') if len(d['extra']) > 90 else d['extra'] or '(none)'}")
    print("Previews: " + (", ".join(f"{n} {p['name']}" for n, p in d["previews"].items()) or "(none: run <numbers>)"))
    print("Approved: " + (", ".join(f"{n} {p['name']}" for n, p in d["approved"].items()) or "(none: approve <numbers>)"))
    print(f"Pack: {d['pack'] or '(none)'}" + "".join(f"\n  uploaded to {k}: {', '.join(v)}" for k, v in d["uploaded"].items()))


# ---------- CLI ----------
def parser():
    ap = argparse.ArgumentParser(prog="python -m sticker_booth.booth", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--session", default="me", help="session folder under sessions/ (default: me)")
    ap.add_argument("--dry-run", action="store_true", help="no Gemini calls (fake previews), no Telegram uploads")
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("photo", help="set the selfie")
    p.add_argument("path")
    p.add_argument("--extra", help="likeness text, or prompts.py names like CLEAN_SHAVEN,COLOURS_BLACK_HAIR_LIGHT_SKIN")
    p.add_argument("--style", choices=sorted(prompts.STYLES))
    sub.add_parser("list", aliases=["menu"], help="numbered prompt menu")
    p = sub.add_parser("add", help="add your own prompt")
    for f in ("name", "emoji", "scene", "palette"):
        p.add_argument(f"--{f}")
    p = sub.add_parser("run", help="make previews: run 10 11 | run dragon | run dev")
    p.add_argument("items", nargs="+")
    p.add_argument("--yes", action="store_true", help="skip the cost question")
    p.add_argument("--again", action="store_true", help="regenerate even if a preview exists")
    p.add_argument("--variations", action="store_true",
                   help="vary pose, expression, props and text; default prompts unchanged without this")
    p.add_argument("--seed", type=int, default=None,
                   help="with --variations: reproduce prompt choices (not identical AI images)")
    p = sub.add_parser("approve", help="turn previews into stickers: approve 11")
    p.add_argument("nums", nargs="+")
    p.add_argument("--pack", help="existing pack name made by your bot (..._by_<bot>)")
    p.add_argument("--yes", action="store_true", help="answer yes to the pack question")
    p.add_argument("--no-upload", action="store_true", help="answer no to the pack question")
    sub.add_parser("status", help="photo, previews, approved, pack")
    return ap


def dispatch(a):
    s = Session(a.session)
    dry = a.dry_run
    {"photo": lambda: cmd_photo(s, a), "list": lambda: cmd_list(s, a), "menu": lambda: cmd_list(s, a),
     "add": lambda: cmd_add(s, a), "run": lambda: cmd_run(s, a, dry), "approve": lambda: cmd_approve(s, a, dry),
     "status": lambda: cmd_status(s, a)}[a.cmd]()


def main(argv=None):
    utf8_console()
    load_env()
    ap = parser()
    a = ap.parse_args(argv)
    if a.cmd:
        return dispatch(a)
    head = (["--session", a.session] + (["--dry-run"] if a.dry_run else []))
    print(f"Sticker booth (session '{a.session}'{', dry run' if a.dry_run else ''}). Commands: photo, list, add, "
          "run, approve, status, help, quit")
    while True:
        try:
            line = input("booth> ").strip()
        except EOFError:
            break
        if line in ("quit", "exit", "q"):
            break
        if not line or line == "help":
            ap.print_help() if line else None
            continue
        try:
            dispatch(ap.parse_args(head + shlex.split(line)))
        except SystemExit as e:  # argparse errors and our messages: stay in the loop
            if e.code not in (0, None):
                print(e.code if isinstance(e.code, str) else "")
        except Exception as e:
            print(f"error: {e}")


if __name__ == "__main__":
    main()
