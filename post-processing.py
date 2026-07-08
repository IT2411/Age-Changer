import os
import subprocess
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

def run_ffmpeg_processing(input_file: Path, output_file: Path):
    """
    Executes an FFmpeg command to center-crop, scale to 630x810,
    and apply moderate blur and grain without over-degrading the image.
    """
    # 1. crop -> Center crop to 630:810 aspect ratio to prevent squeezing
    crop_filter = "crop=w='min(iw,ih*630/810)':h='min(ih,iw*810/630)'"
    
    # 2. scale -> Resize directly to 630x810 (no extreme downsampling)
    scale_filter = "scale=630:810"
    
    # 3. gblur -> Moderate blur (reduced from 2.2 to 1.4)
    blur_filter = "gblur=sigma=1.1"
    
    # 4. eq -> Mild color distortion (keeps colors closer to the original)
    color_distort_filter = "eq=contrast=0.92:saturation=0.85:brightness=0.01"
    
    # 5. noise -> Moderate grain (reduced from 32 to 18)
    grain_filter = "noise=alls=8:allf=u"
    
    # Combine the filters
    filter_graph = (
        f"{crop_filter},"
        f"{scale_filter},"
        f"{blur_filter},"
        f"{color_distort_filter},"
        f"{grain_filter}"
    )
    
    cmd = [
        "ffmpeg",
        "-y",               # Overwrite output files without asking
        "-i", str(input_file),
        "-vf", filter_graph,
        str(output_file)
    ]
    
    # Run command silently
    result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg failed with return code {result.returncode}")

def post_process_pipeline(
    source_folder: str = "age-changed-images", 
    destination_folder: str = "final-passport-images"
):
    """
    Scans the source folder for PNGs, replicates the structure in the destination folder,
    and crops/processes each image using FFmpeg.
    """
    source_path = Path(source_folder)
    dest_path = Path(destination_folder)
    
    if not source_path.exists() or not source_path.is_dir():
        logging.error(f"Source directory '{source_folder}' does not exist. Run the generation script first.")
        return

    # Find all generated PNG files in the subfolders
    VALID_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}

    image_files = [
        f for f in source_path.rglob("*")
        if f.is_file() and f.suffix.lower() in VALID_EXTENSIONS
    ]
    
    if not image_files:
        logging.warning(f"No image files found in '{source_folder}'.")
        return

    logging.info(f"Found {len(image_files)} images to process.")
    dest_path.mkdir(exist_ok=True)

    success_count = 0
    
    for img_file in image_files:
        # Determine relative path to maintain subfolder structure
        relative_path = img_file.relative_to(source_path)
        output_file_path = dest_path / relative_path
        
        # Ensure the destination subfolder exists
        output_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        logging.info(f"Processing: {relative_path}")
        
        try:
            run_ffmpeg_processing(img_file, output_file_path)
            success_count += 1
        except Exception as e:
            logging.error(f"Failed to process {relative_path}: {e}")

    logging.info(f"Post-processing completed. Successfully processed {success_count}/{len(image_files)} images.")

if __name__ == "__main__":
    post_process_pipeline(
        source_folder="input-images",
        destination_folder="final-input-images"
    )