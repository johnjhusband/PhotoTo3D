# CHARACTER.md — the subject's canonical design (from ALL 6 source images in candidates/)

I originally generated from ONE source (`gXAmE1Bn2dubu5B-OCEe4.png`, the umbrella image) and never examined
the other 5. That was a mistake — it dropped her signature headwear. This is the full design, to be
captured in any regeneration. **Use multiple/most source images (multi-image IP-Adapter), not one.**

## Defining features
- **Wide conical straw hat (kasa / sedge hat)** — her SIGNATURE, present in 5 of 6 source images. Was
  MISSING from the final figurine (the umbrella image I used didn't show it). MUST be included.
- **Thin horizontal band across the eyes** (a blindfold-style band; eyes still visible through/around it).
- **Purple/violet eyes**, long brown hair.
- **Snake tongue** — a forked/snake tongue visible in at least one image (the "blood/tongue" detail).
  Likely too fine to 3D-print at 150 mm; noted, not required.
- **Blue scarf / cowl** around the neck (sometimes patterned).
- **Grey ribbed knit dress / kimono-style top**, dark cloak/shawl.
- **Bandage-wrapped arms (and legs)** — purple/grey wraps.
- Holds an **umbrella** in one image (a held prop — NOT headwear; the hat is the headwear).

## Known defects in the current figurine (John's review, to fix next iteration)
1. **Hat missing** — regenerate with the conical straw hat (use the hat-bearing sources + explicit prompt).
2. **Insufficient detail for a 150 mm print** — push generation fidelity (higher-res / better settings /
   multi-view) so a 15 cm print reads as detailed.
3. **Right hand misshapen** — generative hand weakness; needs a cleaner hands pose or a hand-fix pass.

## Fix approach (next regeneration)
- Multi-image A-pose canonical: feed the hat-bearing source images via IP-Adapter (`consolidate.py` takes
  multiple refs) + prompt the wide conical straw hat explicitly → clean A-pose WITH hat.
- Then the existing pipeline (Hunyuan shape → paint → repair → color → print files), with attention to
  detail and the right hand.
