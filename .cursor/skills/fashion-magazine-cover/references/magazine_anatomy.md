# Magazine Cover Anatomy

A magazine cover is an arrangement of about 8 named parts. Knowing their names and what they do helps you commit to a real layout instead of stacking text.

## The parts

### 1. Masthead
The magazine's name at the top — the largest and most-recognizable text on the cover. It's the brand's primary signal.
- **High-fashion (Vogue/Bazaar)**: huge Didone serif, all-caps, single line, centered or flush-left.
- **Character-mag (Newtype/Megami/Nahida-style)**: CJK kanji + smaller English subtitle, often paired with a script display word.
- **Glossy Asian fashion (Vivi/Cawaii/JJ)**: stylized italic serif with a paper-shadow, plus a kanji sub-masthead.
- **Avant-garde (i-D/Dazed)**: tight geometric sans, sometimes a single letter (i-D's `i-D`), heavy/condensed.

### 2. Dateline / Issue Block
Tiny text right under the masthead OR at the top corners: month, year, issue number, price. Sometimes a strapline ("September Issue", "The Volume Issue", "Special Issue of X").

### 3. Hero Coverline
ONE big italic-serif headline that dominates the cover-line hierarchy. It's the story they most want to sell. Usually italic serif (Cormorant / Playfair italic / Bodoni italic). Often has a small subtitle under it.

### 4. Supporting Coverlines
2–4 smaller cover lines flanking the subject — left or right margin, top or bottom. Each is a short headline + a 1–2-line subtitle. They're varied in length on purpose (rhythm). Voice depends on the magazine flavor (see `cover_flavors.md`).

### 5. Cover Star Signature
The subject's name, usually at the bottom in script display (Italianno / Pinyon / Allura). Sometimes a tagline beneath ("special guest from Sumeru", "the new face of Spring"). For non-character mags, this can be omitted in favor of letting the masthead + hero coverline do the work.

### 6. Badge / Seal / Sticker
A small circle or rosette near the top that flags a special feature: "Special Issue", "Collector's Edition", anniversary number, gift-with-purchase. Rotated 5–10° to feel like a sticker. Optional but adds editorial texture.

### 7. Barcode
Always lower-left. Visually correct bars + an EAN-style number. Real ISBN/UPC is misleading — keep the bar pattern but treat the number as decorative. Never use a real one.

### 8. Cover Texture (optional)
Paper grain, halftone dots, scan-line bleed, light grain noise. Adds editorial credibility but easy to overdo. Use only in PIL pipeline (HTML can't render grain consistently across browsers).

## Hierarchy

Cover-line text always has **three tiers**:
1. **Masthead** — biggest, most prominent.
2. **Hero coverline + subject's name signature** — the second-loudest objects.
3. **Supporting coverlines + dateline + badge** — smaller, support roles.

If two elements compete at the same visual weight, the cover feels noisy. Pick one to win.

## Reading order

A reader's eye lands at the masthead, drops to the hero coverline, then sweeps the supporting cover lines, then settles on the signature. Design the layout so this path is natural — don't put the most important headline where the eye lands last.

## Composition zones

Most covers reserve:
- **Top band (0–25% height)** — masthead + dateline + top badge
- **Left+right margins (full height)** — supporting cover lines
- **Center field** — the subject; leave clear or text overlaps the subject's silhouette (usually a bad idea unless deliberate)
- **Bottom band (75–100% height)** — signature + tagline + barcode

If your subject image occupies the full frame (the Nahida case), the cover lines float over the image's negative space (around the figure). Decide which negative-space regions you have BEFORE picking which side each cover line goes on.

## Anti-patterns to avoid

- **Centered same-size stack of cover lines** — reads as a presentation slide, not a magazine.
- **Generic gradient bar across the bottom** — the lazy way to "make text readable". A real cover earns legibility with text color + selective shadow, not a plate.
- **More than 5 cover lines** — even Cosmo doesn't go past 5–6. After that the cover stops feeling editorial and starts feeling like a label.
- **Real barcode numbers** — looks like a UPC the manufacturer should own.
