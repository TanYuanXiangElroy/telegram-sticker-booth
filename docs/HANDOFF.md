# Sticker Booth: maintenance guide

Photo + prompt -> Gemini image edit -> green-screen cleanup -> 512 px sticker -> Telegram pack made by your own bot.

Run every command from the repo root with the venv active (Windows: `venv\Scripts\python -m ...`).

## Files
- `sticker_booth/booth.py`: the friendly front end (`photo`, `list`, `add`, `run 10 11`, `approve 11`, `status`, or an interactive prompt). Its state lives in `sessions/<name>/session.json` and its own prompts in `my_prompts.json`, both git-ignored. It calls generate, postprocess and telegram_pack and has no logic of its own beyond that.
- `sticker_booth/generate.py`: photo or folder -> stickers. Calls Gemini (`gemini-3.1-flash-lite-image`), cleans up each image and writes `out/<photo-stem>/raw/<name>.png` (raw generation), `<name>.png/.webp`, `pack.json` (emoji per file) and `sheet.png` (contact sheet). `--dry-run` prints prompts and cost only. `--from-raw IMG` cleans up an existing green-screen image without calling Gemini. `--extra "..."` appends a sentence to every prompt.
- `sticker_booth/prompts.py`: emoji scenes (`EMOJIS`), styles (`STYLES`: cartoon, cyberpunk, pixel), the prompt `TEMPLATE` and optional extras (`NO_SCENERY`, `ONLY_PERSON`). Optional `--variations` / `--seed` append seeded pose/expression/props/text tweaks (defaults unchanged without the flag; seed reproduces prompt text, not Gemini pixels).
- `sticker_booth/postprocess.py`: the cleanup (chroma key, largest blob, despill, 512 px, stroke), plus `contact_sheet()`. Also a standalone CLI.
- `sticker_booth/telegram_pack.py`: uploads stickers, creates or extends the pack and optionally posts the link to a chat or topic. Standard library only.
- `sticker_booth/env.py`: loads `.env` and makes the Windows console print emoji.
- `notebook/sticker_booth.ipynb`: the same pipeline step by step. `USE_API=False` uses `examples/sample_raw.png`.
- `examples/stickers/`: a finished 8-Bit pack used as reference output and for dry runs.

## Setup
```
python3 -m venv venv && venv/bin/pip install -r requirements.txt     # Windows: py -m venv venv; venv\Scripts\pip ...
cp .env.example .env      # fill in GEMINI_API_KEY, TELEGRAM_BOT_TOKEN, optionally TELEGRAM_USER_ID
```
Keep keys in `.env` (git-ignored). Never paste them in chat, commit them or print URLs that contain the bot token; the scripts never print either key. The cleanup is light (NumPy/SciPy, one image at a time), so it suits a low-CPU server.

Optional Docker: `docker build -t sticker-booth .` then run with `--env-file .env` and bind mounts for `photos/`, `out/` and `sessions/` (see README "Docker"). The image ships code + `examples/` only; never bake keys or user photos into the image.

## Full flow
```
# 1. generate (about $0.034 per sticker; 8 emojis about $0.27). --dry-run first to check cost
python -m sticker_booth.generate photos/friend.jpg --style pixel --out out
#    a folder of photos also works; --emojis laugh,cry for a subset
# 2. review out/friend/sheet.png by eye: face likeness, real clothes colour, clean border, no green fringe.
#    Redo a bad one: delete out/friend/raw/cry.png, then run again with --emojis cry
# 3. find ids (once): the pack owner must press Start in the bot's chat; for groups, the bot must see a message
python -m sticker_booth.telegram_pack --whoami
# 4. optional topic (once): needs Topics on and the bot as admin with Manage Topics
python -m sticker_booth.telegram_pack --make-topic --chat-id <GROUP_ID> --topic-name "Sticker Booth"
# 5. pack: dry run, then for real
python -m sticker_booth.telegram_pack out/friend --user-id <OWNER_ID> --name friend_8bit --title "Friend 8-Bit" --dry-run
python -m sticker_booth.telegram_pack out/friend --user-id <OWNER_ID> --name friend_8bit --title "Friend 8-Bit" --chat-id <OWNER_ID>
```
It prints `https://t.me/addstickers/<name>_by_<botusername>`. With `--chat-id` (plus `--thread-id` for a topic) it also posts the link and the first sticker there. `--chat-id <OWNER_ID>` sends it as a DM to the owner.

## Prompt formula
`TEMPLATE` in prompts.py: `{scene}. Likeness: keep the person's real face ... Style Guidance: {style}. Visual Details: {palette} for background accents/props only; keep natural skin, real hair colour and real clothing exactly as in the photo (same garment, same colours), single thick white die-cut border on flat #00FF00 background, no detached elements.`
- Styles: `pixel` = Sticker Kaki "8-Bit Retro", `cyberpunk` = Sticker Kaki "Cyberpunk", `cartoon` = default.
- The clothing clause is what keeps real shirt colours, so don't remove it. Palette words only colour props.
- If a style draws square background panels, add `--extra "Character and props only, no background scenery or square panel behind the person."` (cartoon already has this).
- Photos with other people or mascots: `--extra "Draw only the main person in the photo; ignore other people, mascots and costumes around them."`
- New emoji: add an entry to `EMOJIS` (file name, scene, palette, optional notes such as `NO_PANEL`/`BIG_TEXT`) and list it in a `PACKS` group (classic, dev, moods, reactions). telegram_pack maps file names to emojis through the same table when a folder has no pack.json.

## Adding to an existing pack
Generate new stickers into a folder, then rerun telegram_pack with the same `--name`, listing the old folders first and the new ones last. It reads the set with getStickerSet and only uploads stickers beyond the current count. It matches by position, so keep the folder order stable. A set holds at most 120; after that, start `<name>2`.

## Telegram rules
- Static sticker: PNG/WEBP, one side exactly 512 px (the booth makes 512x512), 512 KB or less.
- Set name: `<short>_by_<botusername>`, letters/digits/underscores, 64 chars or fewer, starts with a letter. Link `t.me/addstickers/<name>`.
- Up to 50 stickers in createNewStickerSet; the rest go through addStickerToSet; 120 max.
- The owner (`--user-id`) must have pressed Start in the bot's chat, otherwise you get `PEER_ID_INVALID` / "user not found".
- Topic posting/creating: the group has Topics on and the bot is an admin with Manage Topics.
- Rate limit is about 1 msg/s per chat; the script sleeps 1 s per call and honours 429 `retry_after`.
- Only one program may poll getUpdates per token (409 Conflict). telegram_pack only polls in `--whoami`. Don't run that while another program polls the same token. Sending (creating packs, posting) doesn't conflict.

## Gemini errors and cost
- 429 RESOURCE_EXHAUSTED with "limit: 0": the free tier has no image quota, so enable billing. A plain 429 is a rate limit and is retried.
- 402 "prepayment credits are depleted": top up at https://ai.studio/projects.
- Cost is about $0.034 per image with gemini-3.1-flash-lite-image. Fallback: generate in the AI Studio web UI, save the green-screen image, then `python -m sticker_booth.generate --from-raw img.png --emojis laugh --out out`.
- On 402, 429 quota or a bad key the run stops and keeps finished stickers. Rerun the same command to continue.

## Common failures
- Green fringe or missing chunks: rerun `python -m sticker_booth.postprocess in.png out/name` with `--lo`/`--hi` adjusted, or regenerate.
- Green clothing turned see-through: it is outside the main outline; the default fills holes, so don't pass `--keep-holes`.
- Face doesn't look like the person: use a clear, front-facing, well-lit photo and regenerate that emoji.
- `STICKERSET_INVALID` on getStickerSet: the set doesn't exist yet. That's normal; the script creates it.
- `STICKER_PNG_DIMENSIONS`: the image isn't 512 px. Rerun the cleanup.
- `Bad Request: chat not found` / topic errors: wrong chat id (group ids start with -100), or the bot isn't in the group or isn't an admin.
- `--whoami` is empty: press Start in the bot's private chat (and send any message in the group), then retry.
- Emoji print as `?` or crash on Windows: run in Windows Terminal or the Cursor terminal; the CLIs switch the console to UTF-8.

## Friends' consent
Only make packs of people who said yes. Ask before sharing their pack link elsewhere, delete their photos and outputs if they ask, and don't use their photos for anything else. Photos and outputs live in git-ignored `photos/` and `out/`, so never commit them.
