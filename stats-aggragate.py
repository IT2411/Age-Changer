import shutil
from pathlib import Path

INPUT_DIR = Path("final-input-images")
FINAL_DIR = Path("final-passport-images")
OUTPUT_DIR = Path("passport-images-ishaan")

TARGET_AGES = [22, 32, 42, 52, 62]
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

OUTPUT_DIR.mkdir(exist_ok=True)

total_inputs = 0
completed_inputs = 0
incomplete_inputs = 0

copied_originals = 0
copied_outputs = 0

for input_file in INPUT_DIR.iterdir():
    if input_file.suffix.lower() not in VALID_EXTENSIONS:
        continue

    total_inputs += 1

    image_name = input_file.stem
    final_subfolder = FINAL_DIR / image_name

    if not final_subfolder.exists():
        incomplete_inputs += 1
        continue

    expected_files = [
        final_subfolder / f"{image_name}_{age}.png"
        for age in TARGET_AGES
    ]

    if not all(f.exists() for f in expected_files):
        incomplete_inputs += 1
        continue

    completed_inputs += 1

    # Copy original input image
    shutil.copy2(
        input_file,
        OUTPUT_DIR / input_file.name
    )
    copied_originals += 1

    # Copy all 5 generated images
    for img in expected_files:
        shutil.copy2(
            img,
            OUTPUT_DIR / img.name
        )
        copied_outputs += 1

print("\n===== SUMMARY =====")
print(f"Total input images      : {total_inputs}")
print(f"Completed identities    : {completed_inputs}")
print(f"Incomplete identities   : {incomplete_inputs}")
print(f"Originals copied        : {copied_originals}")
print(f"Generated images copied : {copied_outputs}")
print(f"Total files copied      : {copied_originals + copied_outputs}")
print(f"Output folder           : {OUTPUT_DIR}")