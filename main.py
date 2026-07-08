import os
import io
import time
import logging
import subprocess
from pathlib import Path
from PIL import Image
from google import genai
from keys import GOOGLE_API_KEY

# Configure logging to write to both the console and a log file
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("pipeline.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# Initialize the client
client = genai.Client(api_key=GOOGLE_API_KEY)

# Reference style prompts
PROMPTS = {
    "female": {
        22: (
            "A realistic, low-quality 630x810 passport-size identification photo of a 22-year-old Indian woman. "
            "Facing forward, neutral expression. She has simple, straight black shoulder-length hair and a small "
            "dark mole on her left cheek. She is wearing a simple plain white cotton Kurti. Flat, grainy texture "
            "like a low-resolution digital print, plain light grey background. No specs."
        ),
        32: (
            "A realistic, grainy 630x810 passport-style headshot of a 32-year-old Indian woman. She is wearing "
            "slim, modern black-framed specs. Her hair is neatly tied back in a professional bun. She is wearing "
            "a formal blue-and-white striped office shirt. The image has digital noise and low contrast, "
            "looking like a low-dpi corporate ID scan, neutral expression."
        ),
        42: (
            "A realistic, pixelated 630x810 passport photo of a 42-year-old Indian woman. She has a practical "
            "layered bob haircut with subtle grey hairs visible at the roots and a faint linear scar across her "
            "right eyebrow. She is wearing a traditional cotton Saree with a high-neck blouse. Poor, flat lighting, "
            "washed-out off-white background, low-resolution camera quality. No specs."
        ),
        52: (
            "A realistic, low-resolution 630x810 document photo of a 52-year-old Indian woman. She is wearing "
            "rectangular reading glasses. Her hair is salt-and-pepper, styled in a tight low ponytail. She is wearing "
            "a dark maroon Salwar Kameez with a simple dupatta. Faded colors, looking like a printed government "
            "document photo, flat fluorescent lighting."
        ),
        62: (
            "A realistic, low-quality grainy 630x810 headshot of a 62-year-old Indian woman. Her hair is short, "
            "wavy, and predominantly white/grey. The face shows visible deep lines and a small raised mole near "
            "her right temple. She is wearing a simple white widow-style Saree. Vintage, low-grade security camera "
            "texture with overexposed lighting and a plain white background. No specs."
        )
    },
    "male": {
        22: (
            "A realistic, low-quality 630x810 passport-size identification photo of a 22-year-old Indian man. "
            "Clean-shaven, no beard, no mustache. Thick black casual hair and a small dark mole on his left cheek. "
            "He is wearing a plain navy blue round-neck T-shirt. Flat, slightly blurry texture like a low-resolution "
            "phone camera print, neutral expression, plain light grey background."
        ),
        32: (
            "A realistic, grainy 630x810 passport-style headshot of a 32-year-old Indian man. He is wearing "
            "black-framed specs. He has a light stubble beard, a thin mustache, and a neat side-parted hairstyle. "
            "He is wearing a formal white button-down collared shirt. Digital noise and low contrast, "
            "looking like a budget office ID card scan."
        ),
        42: (
            "A realistic, pixelated 630x810 passport-size photo of a 42-year-old Indian man. He has a thick, "
            "full black beard mixed with grey hairs and a heavy mustache. Short buzzcut hair and a faint linear scar "
            "across his right eyebrow. He is wearing a grey polo neck T-shirt. Poor, flat lighting with a "
            "washed-out off-white background. No specs."
        ),
        52: (
            "A realistic, low-resolution 630x810 document photo of a 52-year-old Indian man. He is wearing "
            "rectangular reading glasses. Face is clean-shaven, showing age lines and prominent grey streaks "
            "at the temples. He is wearing a light blue formal shirt with a dark sleeveless sweater vest. "
            "Faded colors, looking like a printed government ID card photo."
        ),
        62: (
            "A realistic, low-quality grainy 630x810 headshot of a 62-year-old Indian man. He has a neatly "
            "trimmed white beard and mustache with a receding white hairstyle. A small raised mole is visible "
            "near his right temple. He is wearing a traditional white cotton Kurta. Vintage, low-grade security "
            "camera texture with overexposed lighting and a plain background. No specs."
        )
    }
}

def detect_gender(input_image: Image.Image) -> str:
    """
    Uses a fast multimodal model call to determine the gender 
    of the subject in the input image. Defaults to 'male' on error.
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Analyze this passport photo. Is the person a male or a female? "
                "Respond with exactly one word: 'male' or 'female'.", 
                input_image
            ]
        )
        detected = response.text.strip().lower()
        if "female" in detected:
            return "female"
        return "male"
    except Exception as e:
        logging.warning(f"    Gender detection failed, defaulting to 'male'. Error: {e}")
        return "male"

def run_ffmpeg_processing(input_file: Path, output_file: Path):
    """
    Executes an FFmpeg command to center-crop, scale to 630x810, 
    and apply moderate blur and noise to simulate a low-quality scan.
    """
    crop_filter = "crop=w='min(iw,ih*630/810)':h='min(ih,iw*810/630)'"
    scale_filter = "scale=630:810"
    blur_filter = "gblur=sigma=1.4"
    color_distort_filter = "eq=contrast=0.92:saturation=0.85:brightness=0.01"
    grain_filter = "noise=alls=18:allf=u"
    
    filter_graph = f"{crop_filter},{scale_filter},{blur_filter},{color_distort_filter},{grain_filter}"
    
    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(input_file),
        "-vf", filter_graph,
        str(output_file)
    ]
    
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with return code {result.returncode}")

def process_folder_pipeline(
    input_folder: str, 
    raw_output_folder: str = "age-changed-images", 
    final_output_folder: str = "final-passport-images",
    test_mode: bool = False
):
    """
    Coordinates scanning, gender detection, image generation, and immediate 
    FFmpeg post-processing, enforcing strict cleanups on half-completed states.
    """
    valid_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    input_path = Path(input_folder)
    raw_path = Path(raw_output_folder)
    final_path = Path(final_output_folder)
    
    # Verify input directory
    if not input_path.exists() or not input_path.is_dir():
        logging.error(f"The input directory '{input_folder}' does not exist.")
        return

    # Gather matching image files
    image_files = [f for f in input_path.iterdir() if f.suffix.lower() in valid_extensions]
    
    if not image_files:
        logging.warning("No valid images found in the specified input folder.")
        return
    
    # Ensure both output directories exist
    raw_path.mkdir(exist_ok=True)
    final_path.mkdir(exist_ok=True)
    
    # Apply test limit if flag is set
    if test_mode:
        logging.info(f"--- Test mode active: Limiting processing to 2 images out of {len(image_files)} total ---")
        image_files = image_files[:2]
    else:
        logging.info(f"Found {len(image_files)} images to process.")

    target_ages = [22, 32, 42, 52, 62]

    try:
        for img_file in image_files:
            image_name = img_file.stem
            logging.info(f"Processing source image: {img_file.name}")
            
            # Setup subdirectories for both outputs
            raw_subfolder = raw_path / image_name
            final_subfolder = final_path / image_name
            
            raw_subfolder.mkdir(exist_ok=True)
            final_subfolder.mkdir(exist_ok=True)
            
            # Evaluate target ages based on state matrix
            ages_to_generate = []
            for age in target_ages:
                output_filename = f"{image_name}_{age}.png"
                raw_file_path = raw_subfolder / output_filename
                final_file_path = final_subfolder / output_filename
                
                raw_exists = raw_file_path.exists()
                final_exists = final_file_path.exists()

                # State matrix evaluation
                if raw_exists and final_exists:
                    # Case 1: Both exist -> Skip
                    logging.info(f"  Age {age} already completed (raw & final exist). Skipping.")
                else:
                    # Case 2, 3, or 4: Mismatch or missing -> Clean up and queue for full generation
                    if raw_exists:
                        logging.info(f"  Age {age}: Raw exists but Final is missing. Queued for deletion & regeneration.")
                    elif final_exists:
                        logging.info(f"  Age {age}: Final exists but Raw is missing. Queued for deletion & regeneration.")
                    else:
                        logging.info(f"  Age {age}: Missing. Queued for generation.")
                    
                    ages_to_generate.append(age)
            
            if not ages_to_generate:
                logging.info(f"  All ages completed for {image_name}. Skipping image completely.")
                continue

            try:
                input_image = Image.open(img_file)
            except Exception as e:
                logging.error(f"Failed to open image {img_file.name}: {e}")
                continue

            # Detect gender
            logging.info("  Analyzing image to detect gender...")
            gender = detect_gender(input_image)
            logging.info(f"  Detected gender: {gender}")

            for age in ages_to_generate:
                output_filename = f"{image_name}_{age}.png"
                raw_file_path = raw_subfolder / output_filename
                final_file_path = final_subfolder / output_filename

                # Apply cleanups on partial files before proceeding
                if raw_file_path.exists():
                    logging.info(f"    Cleaning up incomplete raw file: {raw_file_path}")
                    raw_file_path.unlink()
                if final_file_path.exists():
                    logging.info(f"    Cleaning up incomplete final file: {final_file_path}")
                    final_file_path.unlink()

                logging.info(f"  Generating age {age} for {image_name}...")
                
                base_prompt = PROMPTS[gender][age]
                prompt = (
                    f"{base_prompt} Modify the person in the provided input photo to fit this description. "
                    f"It is critical that you preserve their core facial identity, bone structure, and features "
                    f"from the source photo, updating only the age, clothing, and styling elements described."
                    f"Do not include any text, watermarks, timestamps or additional elements in the output image."
                )

                try:
                    # Gemini API Call to generate raw image
                    response = client.models.generate_content(
                        model="gemini-3.1-flash-image",
                        contents=[prompt, input_image],
                    )
                    
                    image_saved = False
                    for part in response.parts:
                        if part.inline_data is not None:
                            raw_bytes = part.inline_data.data
                            generated_image = Image.open(io.BytesIO(raw_bytes))
                            generated_image.save(raw_file_path, "PNG")
                            logging.info(f"    Saved raw image: {raw_file_path}")
                            image_saved = True
                            break
                    
                    if not image_saved:
                        logging.warning(f"    No image data returned for age {age}.")
                        continue

                    # Immediately run FFmpeg on the new raw image
                    logging.info(f"    Post-processing raw image with FFmpeg...")
                    run_ffmpeg_processing(raw_file_path, final_file_path)
                    logging.info(f"    Saved final processed image: {final_file_path}")
                    
                    # Brief pause between loops to manage API rate limits
                    time.sleep(1)

                except Exception as e:
                    logging.error(f"    Failed during processing of age {age}: {e}")

    except KeyboardInterrupt:
        logging.warning("\nPipeline execution paused by user (Ctrl+C captured).")
        logging.info("Run the script again to resume processing remaining images.")

# Run the pipeline
process_folder_pipeline(
    input_folder="input-images",
    test_mode=False  # Set to False to run on the entire folder
)