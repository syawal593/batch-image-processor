import os
import zipfile
from PIL import Image

# 1. MULTIPROCESSING: Fungsi berat untuk CPU (Resize & Konversi ke WebP)
def process_single_image(file_path: str, output_dir: str, target_width: int = 800):
    try:
        base_name = os.path.basename(file_path)
        name, _ = os.path.splitext(base_name)
        output_path = os.path.join(output_dir, f"{name}_processed.webp")
        
        with Image.open(file_path) as img:
            w_percent = (target_width / float(img.size[0]))
            h_size = int(float(img.size[1]) * float(w_percent))
            img_resized = img.resize((target_width, h_size), Image.Resampling.LANCZOS)
            img_resized.save(output_path, "WEBP", quality=80)
            
        return {"filename": base_name, "status": "success", "output": output_path}
    except Exception as e:
        return {"filename": os.path.basename(file_path), "status": "error", "message": str(e)}

# 2. MULTITHREADING: Fungsi I/O-bound untuk kompresi file ZIP
def create_zip_archive(processed_files, zip_filename):
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for file_path in processed_files:
            if os.path.exists(file_path):
                zipf.write(file_path, arcname=os.path.basename(file_path))