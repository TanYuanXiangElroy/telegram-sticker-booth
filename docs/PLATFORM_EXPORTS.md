# Platform sticker export research

Status: **research / documentation**. This is not a claim that a universal ZIP installs packs on every app.

Telegram (this repo's primary target) already has Bot API pack creation. Other apps differ: some need a companion app or store listing, some only support sending images as ordinary media.

| Platform | Native pack install? | Automatic image conversion enough? | Feasible exporter in this repo? |
|---|---|---|---|
| Telegram | Yes (own bot / @Stickers) | Partial | Already shipped (`telegram_pack`) |
| WhatsApp | Yes, via sticker *app* or in-app creator — **not** by opening a random ZIP | Need WebP ≤100 KB, 512×512 | Yes: recompress WebP (separate PR) |
| Signal | Yes, via Signal Desktop sticker creator — not a blind ZIP install | PNG/WebP ~512, ≤300 KB | Mostly already OK; folder export + instructions |
| Discord | Guild stickers (Boost); not a portable “pack ZIP” | PNG 320×320, ≤512 KB | Yes: resize PNG (separate PR) |
| LINE | Creators Market submission / custom stickers — review + tooling | PNG max 370×320, etc. | Resize helper possible; **not** auto-publish |
| iMessage | Xcode sticker pack / Messages app — developer tooling | App Store / Xcode project | Docs only unless we add a scaffold later |
| WeChat | Official sticker / emotion store processes; no simple open ZIP | Treat as **ordinary image sharing** unless using WeChat’s own tools | Honest “share images” only |

## Sources (verify before shipping marketers’ claims)

- WhatsApp FAQ (Android): https://faq.whatsapp.com/1056840314992666/?cms_platform=android — static 512×512, **≤100 KB**, WebP; packs via WhatsApp sticker apps ([WhatsApp/stickers](https://github.com/WhatsApp/stickers)).
- Signal Support: https://support.signal.org/hc/en-us/articles/360031836512-Stickers — Desktop creator; PNG/WebP; ≤300 KB; resize to 512; up to 200 stickers.
- Discord Creators FAQ: https://support.discord.com/hc/en-us/articles/4402687377815 — **320×320** PNG/APNG; ≤512 KB; server Boost for custom stickers.
- Discord API: https://docs.discord.com/developers/resources/sticker — upload constraints 320×320, 512 KiB.
- LINE Creators Market: https://creator.line.me/en/guideline/sticker/ — sticker images max **370×320** PNG, transparent, ≤1 MB; main 240×240; tab 96×74; set sizes 8/16/24/32/40.
- iMessage: Apple sticker pack / Xcode templates (App Store distribution) — not a consumer ZIP drop-in.
- WeChat: no verified consumer “import this ZIP as a sticker pack” path found for third-party hobby tools; label as image sharing unless using WeChat’s official creator flows.

## What this project will implement (follow-up PRs)

1. **WhatsApp WebP recompress** — export folder of ≤100 KB 512×512 WebP + README that points to WhatsApp’s sticker app / in-app flow (not “Telegram ZIP installs on WhatsApp”).
2. **Discord 320 PNG** — resize/pad to exactly 320×320 PNG ≤512 KB + README for Server Settings → Stickers.
3. **Signal folder** — copy/verify ≤300 KB assets + Desktop creator steps (no fake “Signal ZIP install”).
4. **LINE resize** — optional max 370×320 PNG helper + Creators Market steps (submission is manual).
5. **iMessage / WeChat** — documentation only until a verifiable, non-misleading path exists.

Do not advertise universal ZIP importing or automatic pack installation across messengers.
