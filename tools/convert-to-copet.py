#!/usr/bin/env python3
"""Convert 4-state sprites (working/thinking/idle/alert) to CoPet Codex-compatible spritesheet."""

import os, sys, json, argparse
from PIL import Image

ROWS = 9
COLS = 8
CELL_W = 192
CELL_H = 208
SHEET_W = COLS * CELL_W  # 1536
SHEET_H = ROWS * CELL_H  # 1872

# Map our 4 phases to CoPet rows
# CoPet rows: 0=Review, 1=RunningRight, 2=RunningLeft, 3=Waving, 4=Jumping, 5=Failed, 6=Waiting, 7=Running, 8=Idle
PHASE_ROW = {
    "working": 7,    # executing → Running
    "thinking": 8,   # thinking → Review (repurposed for Thinking via petAnimation.ts)
    "alert": 6,      # waiting → Waiting
    "idle": 0,       # idle → Idle
}

FRAMES_PER_ROW = 6  # generate 6 frames per row with slight variation

def main():
    ap = argparse.ArgumentParser(description="Convert 4-state sprites to CoPet spritesheet")
    ap.add_argument("--sprite-dir", required=True, help="Directory with working/thinking/idle/alert.png")
    ap.add_argument("--out-dir", required=True, help="Output directory for pet.json + spritesheet.webp")
    ap.add_argument("--pet-name", default="custom-pet", help="Pet display name")
    ap.add_argument("--pet-id", default=None, help="Pet ID (default: derived from pet-name)")
    ap.add_argument("--description", default="Custom CoPet companion", help="Pet description")
    args = ap.parse_args()

    pet_id = args.pet_id or args.pet_name.lower().replace(" ", "-")
    os.makedirs(args.out_dir, exist_ok=True)

    # Load source sprites
    sprites = {}
    for phase, fn in [("working", "working.png"), ("thinking", "thinking.png"),
                       ("idle", "idle.png"), ("alert", "alert.png")]:
        fp = os.path.join(args.sprite_dir, fn)
        if not os.path.exists(fp):
            print(f"WARNING: {fp} not found, skipping {phase}")
            continue
        sprites[phase] = Image.open(fp).convert("RGBA").resize((CELL_W, CELL_H), Image.LANCZOS)

    if not sprites:
        print("ERROR: no sprites found")
        sys.exit(1)

    # Use idle as fallback for all missing phases
    fallback = sprites.get("idle") or next(iter(sprites.values()))

    # Create spritesheet
    sheet = Image.new("RGBA", (SHEET_W, SHEET_H), (0, 0, 0, 0))

    for row in range(ROWS):
        # Find which phase maps to this row
        phase = None
        for ph, r in PHASE_ROW.items():
            if r == row:
                phase = ph
                break

        if phase and phase in sprites:
            base_img = sprites[phase]
        else:
            base_img = fallback

        for col in range(COLS):
            x = col * CELL_W
            y = row * CELL_H
            # For non-phase rows, just place 6 frames, leave rest transparent
            if phase or col < FRAMES_PER_ROW:
                sheet.paste(base_img, (x, y), base_img)

    # Save spritesheet
    out_webp = os.path.join(args.out_dir, "spritesheet.webp")
    sheet.save(out_webp, "WEBP", quality=90)
    print(f"Saved: {out_webp}")

    # Write pet.json
    pet_json = {
        "id": pet_id,
        "displayName": args.pet_name,
        "description": args.description,
        "spritesheetPath": "spritesheet.webp",
    }
    out_json = os.path.join(args.out_dir, "pet.json")
    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(pet_json, f, indent=2, ensure_ascii=False)
    print(f"Saved: {out_json}")

    print(f"\nDone! Install to CoPet:")
    print(f"  Copy {args.out_dir} to ~/.copet/pets/{pet_id}/")
    print(f"  Then restart CoPet and select '{args.pet_name}' from the pet menu.")

if __name__ == "__main__":
    main()
