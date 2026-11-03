"""Edit me! Emoji scenes, palettes and styles.

Each emoji: (file_name, scene, palette[, notes]). The final prompt is built from TEMPLATE below
(the Sticker Kaki formula), then the optional per-sticker notes. Keep scenes starting with
"The person in the photo ...". Stickers are grouped into PACKS; --emojis takes a pack name
(classic, dev, moods, reactions), 'all', or a comma list of names/emojis.
"""

# Appended to the newer entries: Gemini likes to paint a square scene behind the person.
NO_PANEL = "No square background panel behind the person; only the person and their props."
# For stickers with words: spell them out letter by letter in the scene too.
BIG_TEXT = "Any text is spelled exactly as given, in big bold blocky pixel letters that are easy to read at small size."

EMOJIS = {
    "😂": ("laugh", "The person in the photo laughing so hard that big cartoon tears of joy fly off their face, holding their belly",
           "bright sunny yellow and orange"),
    "👍": ("thumbs_up", "The person in the photo giving a big confident thumbs-up with a wink and a grin",
           "fresh sky blue and lime"),
    "❤️": ("heart", "The person in the photo making a heart shape with both hands, smiling warmly, with a few little hearts around them",
           "soft pink and red"),
    "😭": ("cry", "The person in the photo crying dramatically with waterfall streams of cartoon tears, mouth wide open in despair",
           "cool blue and lavender"),
    "😡": ("angry", "The person in the photo furious with a red face, clenched fists and steam puffing out of their ears",
           "fiery red and charcoal"),
    "🎉": ("party", "The person in the photo celebrating with arms up, wearing a party hat, with a party popper bursting confetti",
           "rainbow confetti with purple and gold"),
    "🤔": ("think", "The person in the photo thinking hard with a hand on their chin, one eyebrow raised, a question mark above their head",
           "calm teal and mint"),
    "😴": ("sleep", "The person in the photo fast asleep slumped over a laptop, drooling a little, with floating Zzz letters",
           "sleepy navy and soft lilac"),

    # --- dev booth (themes from Google's Sticker Kaki booth at Build with Gemini Singapore) ---
    "🧻": ("chope", "The person in the photo at a hawker centre table, cheekily placing a small packet of tissue paper on the "
           "table to reserve the seat, a steaming bowl of noodles beside it, with a big comic speech bubble that says "
           "\"CHOPE!\"",
           "hot pink, cyan and yellow", f"{NO_PANEL} {BIG_TEXT}"),
    "🐉": ("dragon", "The person in the photo riding on the back of a friendly teal pixel dragon, one fist raised in "
           "triumph, the dragon breathing a blast of blue and orange fire at a few tiny cartoon software bugs",
           "teal, flame orange and electric blue", f"{NO_PANEL}"),
    "🏖️": ("error404", "The person in the photo happily away on leave, relaxing with a small backpack and a cold drink, "
            "giving a thumbs-up, next to a retro computer error pop-up window that reads \"ERROR 404: EMPLOYEE ON LEAVE\"",
            "sunny yellow, leafy green and sky blue accents",
            f"The pop-up window sits right next to him; no landscape, sky or scenery behind. {NO_PANEL} {BIG_TEXT}"),
    "😐": ("please_advise", "The person in the photo at a laptop with a flat, deadpan, unimpressed office face, half-lidded "
           "eyes but frazzled messy hair and a sweat drop, buried up to the chest in chaotic towering piles of "
           "paperwork, papers flying through the air, several coffee cups (one tipped over), sticky notes stuck "
           "everywhere that read \"PLEASE REVERT ASAP\" and \"URGENT\", and one big sign above it all that says "
           "\"PLEASE ADVISE\" as the largest text",
           "office beige, pastel blue and highlighter yellow",
           f"\"PLEASE ADVISE\" stays the biggest, clearest words in the sticker. {NO_PANEL} {BIG_TEXT}"),

    # --- moods (pose ideas from classic chat stickers, drawn as the person) ---
    "😔": ("sad_drink", "The person in the photo sitting glumly at a short bar counter, head hung low looking down, eyes "
           "closed, next to a glass of iced drink and a small ashtray with a smoking cigarette, a lonely end-of-the-day mood",
           "dusky purple and amber", f"Only a short piece of bar counter under the glass; no bar room, wall or window behind. {NO_PANEL}"),
    "😞": ("sad", "The person in the photo standing just sad in general: droopy shoulders, eyes closed, a small frown, "
           "arms hanging limp, the whole body sagging",
           "muted grey-blue", NO_PANEL),
    "😶": ("corner", "The person in the photo seen from above, lying curled up face-down in the corner where two walls "
           "meet on a small square of grey floor, defeated and hiding from the world",
           "cool grey and pale blue", "Only a small patch of floor and the two wall edges, no other scenery."),
    "📞": ("on_phone", "The person in the photo lying on their belly on the floor, legs kicked up behind, happily chatting "
           "on an old pink rotary telephone, holding the pink receiver to their ear, a long curly phone cord looping to "
           "the phone in front of them",
           "bubblegum pink and cream", NO_PANEL),
    "🥲": ("single_tear", "The person in the photo smiling bravely with pressed lips, trying to hold it together, one "
           "single round tear rolling down one cheek, eyebrows tilted up",
           "soft blue and peach", NO_PANEL),
    "😅": ("clueless_call", "The person in the photo on a work video call at a laptop, wearing a headset, with a blank "
           "'no idea what I am doing' stare, a big sweat drop on the forehead, standing stiffly with arms at the sides",
           "corporate navy and light blue", f"Costume: for this sticker they wear a dark grey business suit, white "
           f"shirt and light blue tie instead of the photo clothing. {NO_PANEL}"),

    # --- reaction emojis drawn as the person ---
    "🤡": ("clown", "The person in the photo as a goofy clown: their own normal hairstyle, white clown face paint with "
           "big red smile lines, a round red clown nose, a tiny polka-dot clown party hat perched on top of their own "
           "hair and a small frilly ruff collar, a silly self-mocking grin, holding a small horn",
           "primary red, yellow and blue",
           f"Costume: face paint, red nose, tiny hat and ruff collar are allowed; no wig and no coloured hair, keep "
           f"their real hair and glasses. {NO_PANEL}"),
    "💀": ("skull", "The person in the photo 'dead' from laughing: flopped over backwards, laughing with tears, while a "
           "small cute cartoon ghost of them floats up from their body holding a tiny cute skull",
           "spooky purple and bone white", f"Keep it cute and funny, not scary or gory. {NO_PANEL}"),
    "🤷‍♂️": ("shrug", "The person in the photo doing a big shrug, palms up, shoulders raised, eyebrows up, a "
             "half-smile that says 'I don't know'",
             "light grey and soft yellow", NO_PANEL),
    "🙇‍♂️": ("bow", "The person in the photo in a deep apologetic bow from the waist, hands at their sides, head down, "
             "seen from the side, a small sweat drop and two little 'sorry' motion lines",
             "calm beige and soft red", NO_PANEL),
    "🙇": ("dogeza", "The person in the photo doing a full Japanese dogeza apology, seen from the side in a "
           "three-quarter view: kneeling in seiza with knees and shins flat on the floor, the whole upper body folded "
           "all the way forward and down so the back is low and almost flat, the forehead pressed right onto the "
           "floor between both hands, which lie flat on the floor in front of the head; the head is turned slightly "
           "toward the viewer so the face, glasses and black hair are still clearly visible; cute and very "
           "apologetic, with a small sweat drop and a small soft oval shadow on the floor under them",
           "calm beige and soft red", f"No mat, rug, tatami or floor tiles: only a small soft shadow. {NO_PANEL}"),
    "🚑": ("ambulance", "The person in the photo lying on their back on a white hospital stretcher, a white bandage "
           "wrapped around their head with a small plaster on the cheek, eyes spiralled and dazed, one hand raised "
           "weakly, with a comic speech bubble that says \"SEND HELP\", a tiny red-cross ambulance light beside "
           "the stretcher, cute and funny",
           "ambulance red and white", f"Cute, not gory: no blood. {NO_PANEL} {BIG_TEXT}"),
}

PACKS = {
    "classic": ["😂", "👍", "❤️", "😭", "😡", "🎉", "🤔", "😴"],
    "dev": ["🧻", "🐉", "🏖️", "😐"],
    "moods": ["😔", "😞", "😶", "📞", "🥲", "😅"],
    "reactions": ["🤡", "💀", "🤷‍♂️", "🙇‍♂️", "🚑", "🙇"],
}

STYLES = {
    # default: bold modern cartoon
    "cartoon": "Bold, clean 2D cartoon sticker illustration like a modern animated series, character and props only with no background scenery, thick black outlines, "
               "flat vibrant cel-shading, simplified shapes, playful proportions with a slightly larger head, "
               "big exaggerated expression, faithful facial likeness to the person in the photo",
    # Sticker Kaki "Cyberpunk"
    "cyberpunk": "Futuristic cyberpunk tech sticker illustration, sci-fi neon glow accents, subtle circuit patterns "
                 "and HUD energy details, dark sleek aesthetic with bright neon pop colors, faithful facial likeness "
                 "to the person in the photo",
    # Sticker Kaki "8-Bit Retro"
    "pixel": "Authentic 8-bit retro arcade pixel art sticker illustration, 8-bit pixel grid details, crisp pixelated "
             "edges, bold black outline, faithful facial likeness to the person in the photo",
}

TEMPLATE = (
    "{scene}. Likeness: keep the person's real face — same face shape, eyes, eyebrows, nose, mouth, hairstyle "
    "and hair colour, skin tone, facial hair and glasses as in the photo — instantly recognisable. "
    "Only draw a beard, moustache or stubble if one is clearly visible in the photo; otherwise draw the face "
    "clean-shaven, and don't turn chin or upper-lip shadows into stubble. "
    "Colour lock: the hair is exactly the photo's hair colour (dark or black hair stays jet black with only dark grey "
    "highlights, never brown or auburn); the skin is the photo's own natural skin tone, evenly lit, with no pink blush, "
    "no red cheeks and no yellow or orange tint, and the same skin colour on face, neck and hands. "
    "Style Guidance: {style}. Visual Details: {palette} palette for the background accents and props only; "
    "keep natural skin tone, the person's real hair colour, and their real clothing exactly as in the photo with the same garment type and the same colours, single continuous thick white die-cut sticker border "
    "on a flat #00FF00 background (all props and accents connected inside the border, no detached floating elements)."
)

# Optional extra sentences you can append with build_prompt(..., extra=...)
NO_SCENERY = "Character and props only, no background scenery or square panel behind the person."
ONLY_PERSON = "Draw only the main person in the photo; ignore other people, mascots and costumes around them."
# Per-person colour lock, measured from the photo (hex = how the colours should look in the sticker).
# Example for a black-haired person with light skin; pass it with --extra or build_prompt(..., extra=...).
COLOURS_BLACK_HAIR_LIGHT_SKIN = ("Hair colour: jet black, about #141418, never brown. Skin colour: light warm tan, about "
                                 "#F5C29C in the lit areas with slightly darker #E0A684 shading, the same on every "
                                 "sticker, never pink, red, yellow or orange.")

# Facial-hair lock for a clean-shaven person; append next to their colour extra (not in TEMPLATE: other people may have a beard).
CLEAN_SHAVEN = "Clean-shaven: no beard, no moustache, no stubble, smooth chin and upper lip."

NAMES = {v[0]: k for k, v in EMOJIS.items()}  # 'laugh' -> '😂'


def resolve_emojis(spec="classic"):
    """'all', a pack name from PACKS, or a comma list of emojis, names and/or packs ('😂,thumbs_up,dev').
    Returns emoji keys of EMOJIS."""
    if spec == "all":
        return list(EMOJIS)
    norm = {k.replace("\ufe0f", ""): k for k in EMOJIS}
    out, bad = [], []
    for e in (x.strip() for x in spec.split(",")):
        if not e:
            continue
        if e in PACKS:
            out += [k for k in PACKS[e] if k not in out]
            continue
        k = NAMES.get(e) or norm.get(e.replace("\ufe0f", "")) or (e if e in EMOJIS else None)
        (out if k else bad).append(k or e)
    if bad:
        raise ValueError(f"Unknown emoji {bad}. Choose from: {' '.join(EMOJIS)} (or names: {', '.join(NAMES)}; "
                         f"or packs: {', '.join(PACKS)}, all)")
    return out


def build_prompt(emoji, style="cartoon", extra=""):
    _, scene, palette, *notes = EMOJIS[emoji]
    p = TEMPLATE.format(scene=scene, style=STYLES[style], palette=palette)
    return " ".join([p, *notes, extra]).strip()
