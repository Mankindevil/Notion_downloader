# Clarification Prompts

When the input image is ambiguous, the skill MUST ask the user instead of guessing. This doc has the decision rule and pre-baked `AskUserQuestion` templates for each ambiguous case.

> See also: the user's persistent feedback `feedback_ask_creative_direction` — ask before assuming subjective choices.

## Default assumption — adult OC

Every input subject is the user's **original character (OC), adult**. The skill does NOT try to identify the subject as a franchise character. Published characters (Nahida, Chloe, etc.) appear in the references only as *visual-language anchors* — palette / font / decoration inspiration when the OC happens to read like them. Never ask "is this Nahida?" Ask "tell me about your OC".

## When to ask vs decide silently

| Situation | Action |
|---|---|
| Any input subject | **Always treat as adult OC** — confirm OC name + 1-line vibe (template 5) |
| OC visually resembles a published character | **Decide silently** — borrow that character's palette/fonts as inspiration, don't name-claim the OC |
| Mixed mood signals (cheerful pose + dark palette, etc.) | **Ask** — which mood should dominate |
| User has named a magazine ("Vogue style", "ViVi style") | **Decide silently** — use catalog entry |
| Effects intensity (always) | **Ask** — confirm FX before applying |
| Aspect ratio | **Decide silently** — from input image dims |
| Single dominant color in image | **Decide silently** — extract palette |
| 3+ competing colors / desaturated image | **Ask** — which palette to prioritize |
| Layered export | **Decide silently** — on by default |

## Templates

### 1 — Magazine flavor (use when subject is non-franchise / real person / OC)

```python
AskUserQuestion(questions=[{
    "question": "What magazine flavor fits this subject?",
    "header": "Mag flavor",
    "multiSelect": True,
    "options": [
        {
            "label": "High-fashion editorial (Vogue / Bazaar) (Recommended)",
            "description": "Single huge Didone masthead, sparse confident cover lines, restrained palette. Works for striking portraits and confident subjects."
        },
        {
            "label": "Avant-garde (i-D / Dazed / Numéro)",
            "description": "Heavy condensed sans masthead, deadpan lowercase italic cover lines, single accent rule, off-axis composition. Good for edgy or unconventional subjects."
        },
        {
            "label": "Asian fashion glossy (ViVi / Cawaii)",
            "description": "Italic display masthead with paper-shadow, multi-color cover lines, sparkles, gold price badge. Good for playful/cute subjects."
        },
        {
            "label": "Bilingual character-mag",
            "description": "CJK kanji + italic-script English masthead, in-universe cover lines, character signature. Designed for anime/game characters but works for any subject if you want this aesthetic."
        }
    ]
}])
```

### 2 — Mood picker (use when image signals mix)

```python
AskUserQuestion(questions=[{
    "question": "Which mood should the cover lean into?",
    "header": "Mood",
    "multiSelect": False,
    "options": [
        {"label": "Dreamy / regal", "description": "Soft palette, italic serifs, light atmospheric effects, signature-led composition."},
        {"label": "Cheeky / playful", "description": "Hot colors, hearts/sparkles, multi-color cover lines, busier layout."},
        {"label": "Edgy / cinematic", "description": "Deeper contrast, cooler grade, sparse text, off-axis composition."},
        {"label": "Restrained / editorial", "description": "Minimal text, big masthead, restrained palette — Vogue territory."}
    ]
}])
```

### 3 — FX intensity (ALWAYS ask before applying any FX, per user preference)

```python
AskUserQuestion(questions=[{
    "question": "Apply atmospheric effects to the covers?",
    "header": "FX",
    "multiSelect": False,
    "options": [
        {
            "label": "Subtle (Recommended)",
            "description": "Vignette + soft rim light + optional color grade. Adds depth without changing the photograph's character."
        },
        {
            "label": "Expressive",
            "description": "Above plus sparkles / lens flare / paper grain where the variant supports it. Good for character-mag and glossy flavors. May feel over-produced for restrained editorial."
        },
        {
            "label": "None",
            "description": "Flat output — no overlays, no grading. Cleanest pipeline; covers feel less art-directed."
        }
    ]
}])
```

### 4 — Palette confirmation (use when colors are ambiguous)

```python
AskUserQuestion(questions=[{
    "question": "Which palette should the cover use?",
    "header": "Palette",
    "multiSelect": False,
    "options": [
        {
            "label": "Auto-extract from image (Recommended)",
            "description": "Pull dominant colors from the subject (hair / eyes / outfit). Best when the image has clear color identity."
        },
        {
            "label": "User-named (specify in chat)",
            "description": "Tell me the ink / accent / paper colors directly. Best when you have a brand or franchise reference."
        },
        {
            "label": "Black + white + one accent",
            "description": "Restrained Vogue-style palette. Works for almost any subject."
        }
    ]
}])
```

### 5 — OC intake (use on every new subject)

Every subject is the user's adult OC. Ask for the name and a 1-line vibe so the cover speaks the right language. This is the default opener — replaces the old "is this a recognized character?" flow.

```python
AskUserQuestion(questions=[{
    "question": "What's the OC's name + 1-line vibe? (e.g. 'Mira — gothic librarian who moonlights as a fencer')",
    "header": "OC intake",
    "multiSelect": False,
    "options": [
        {"label": "I'll type the name + vibe in chat", "description": "Free-form: drop the name and a one-sentence personality so I can pick palette/fonts/decoration vocab."},
        {"label": "Just use a placeholder name", "description": "Skip the naming — use a generic signature. You can edit it later in cover_config.json."}
    ]
}])
```

Optionally follow up with: *"Does your OC visually remind you of any published character? Naming one lets me borrow that character's palette/fonts as a reference — your OC stays the subject."* Only ask this if the visual mood is genuinely ambiguous; usually you can derive everything from the OC name + vibe + image.

### 6 — Aspect ratio override (rare — use only if user wants to crop or pad)

```python
AskUserQuestion(questions=[{
    "question": "Input is {orientation} ({W}×{H}). Match it, or convert?",
    "header": "Aspect",
    "multiSelect": False,
    "options": [
        {"label": "Match input — keep {orientation} (Recommended)", "description": "Output preserves the input's aspect ratio. No cropping."},
        {"label": "Convert to portrait 3:4", "description": "Crop or pad the input to a standard magazine portrait. May lose edges of the image."},
        {"label": "Convert to landscape 4:3", "description": "For pinterest/desktop wallpaper covers. May lose top/bottom of a portrait image."}
    ]
}])
```

## Asking discipline

- Never stack more than 3 questions in a single AskUserQuestion call. The user will get fatigued.
- Lead with the most-impactful question (usually flavor or mood). Other questions can wait until you have the answer to the first.
- The "Recommended" tag in option labels is for the option YOU would pick if forced — give the user a clear default to accept.
- If the user gives a confident creative direction in the initial prompt ("make me a Vogue-style cover of Nahida"), DON'T ask flavor — they already answered.
- After the user picks, summarize the design decision in 1–2 sentences before running the export. Lets them course-correct.
