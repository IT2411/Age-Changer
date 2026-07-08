# Passport Age-Progression Pipeline

This pipeline automates the generation of age-progressed passport photos (ages 22, 32, 42, 52, and 62) from a folder of source images. 

Using the **Google GenAI SDK (Gemini)**, the system automatically detects the gender of the subject in each input image, applies tailored style and clothing prompts, generates the aged variations, and immediately post-processes them with **FFmpeg** to apply realistic passport-style cropping, soft blur, and print grain.

---

## Features
* **Automated Gender Detection**: Uses `gemini-2.5-flash` to identify gender and dynamically apply style/clothing prompts.
* **Age-Specific Styling**: Progresses subjects through 5 distinct age-appropriate style variations (such as changing clothing, hair, and accessories).
* **Robust Pause & Resume**: If interrupted, the script skips fully completed files on the next run to save your API quota.
* **Consistent Aspect Ratio (No Squeezing)**: Uses FFmpeg to dynamically center-crop inputs to a 630x810 ratio before scaling.
* **Analog Effects**: Automatically applies customizable blur, minor desaturation, and scanning grain.
* **Unified Output**: Creates organized subfolders for both raw AI generations and post-processed results.

---

## Prerequisites

### 1. System Dependencies
You must have **FFmpeg** installed on your system and added to your system's PATH.
* **Mac** (via Homebrew): `brew install ffmpeg`
* **Windows** (via winget): `winget install Gyan.FFmpeg`
* **Linux** (Debian/Ubuntu): `sudo apt update && sudo apt install ffmpeg`

Verify your installation by running `ffmpeg -version` in your terminal.

### 2. Python Dependencies
Install the required Python packages:
```bash
pip install google-genai pillow
```

---

## File Structure

Arrange your workspace directory as follows:

```text
├── keys.py                    # Contains your Gemini API key
├── main.py                    # The core pipeline script
├── ishaan/                    # Your input folder containing source photos
│   ├── image1.jpg
│   └── image2.png
├── age-changed-images/        # Generated automatically (Raw outputs)
├── final-passport-images/     # Generated automatically (Post-processed outputs)
└── pipeline.log               # Generated automatically (Process logs)
```

### Setup `keys.py`
Create a file named `keys.py` in the same directory as `main.py` and add your API key:
```python
# keys.py
GOOGLE_API_KEY = "YOUR_ACTUAL_GEMINI_API_KEY"
```

---

## Usage

To start the pipeline, run the script:

```bash
python main.py
```

### Script Configurations (in `main.py`)
At the bottom of `main.py`, you can configure how the script executes:

```python
process_folder_pipeline(
    input_folder="input_folder",     # Your source images folder
    raw_output_folder="age-changed-images",
    final_output_folder="final-passport-images",
    test_mode=True                   # Set to True to process only 2 images first, or False for the full run
)
```

---

## How It Works

### 1. Gender Recognition & Style Matching
For each image in your source folder, the script queries `gemini-2.5-flash` to classify the subject as male or female. Based on this, it selects the appropriate prompt series from the predefined template collection to change clothes, hair, and visible age features.

### 2. Output Storage
Outputs are neatly structured into subfolders matching the original filename:

```text
final-passport-images/
└── image1/
    ├── image1_22.png
    ├── image1_32.png
    ├── image1_42.png
    ├── image1_52.png
    └── image1_62.png
```

### 3. Verification & Resume Safety
Before calling the API, the pipeline checks if `final-passport-images/<image_name>/<image_name>_<age>.png` already exists. If present, it skips the generation. If you press `Ctrl+C` to pause the script, you can restart it later without wasting API calls on already completed photos.