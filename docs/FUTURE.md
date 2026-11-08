# Future improvements (planned, not shipped)

These items are **backlog ideas**. None of them are implemented by this document alone.

## Model comparison

- Run the same photos and prompts across image models.
- Record likeness, text accuracy, style consistency, cutout quality, cost and speed.
- Keep results private unless example assets are approved for publication.

## More packs and styles

- Additional emoji packs and visual styles beyond cartoon / cyberpunk / pixel.
- Keep the clothing / likeness / green-screen formula unless a style needs an explicit exception.

## Web UI

- Browser UI for photo → preview → approve.
- **Secure handling of user-owned keys** (bring-your-own Gemini / bot token).
- Never embed a shared bot token in frontend code or public client bundles.

## Better cutouts

- Harder green clothing and enclosed background patches between limbs.
- Tunable chroma / hole-punch without punching real green props incorrectly.

## Review UX

- Side-by-side previews, selective rerolls and explicit approval before export/upload.
- Batch-cost controls, bounded retries and resumable runs (skip finished raws — partially exists today).

## Automated quality checks

- Detect cropped subjects, unreadable text, wrong dimensions, oversized files and invalid exports before upload.

## Platform exporters

- See `docs/PLATFORM_EXPORTS.md`. Prefer small, honest converters over “universal pack install” marketing.
