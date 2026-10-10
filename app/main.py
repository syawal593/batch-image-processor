import os
import shutil
import asyncio
import json
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse

from app.config import UPLOAD_DIR, PROCESSED_DIR
from app.processors import process_single_image, create_zip_archive

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = os.path.join("app", "templates", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Error: index.html tidak ditemukan</h1>"

@app.post("/process-stream")
async def process_stream(files: list[UploadFile] = File(...)):
    async def event_generator():
        try:
            # TAHAP 1: Non-Blocking Upload
            yield f"data: {json.dumps({'step': 1, 'text': 'Tahap 1: Menerima & menyimpan file secara Non-Blocking (Async)...'})}\n\n"
            await asyncio.sleep(0.5)
            
            saved_files = []
            for file in files:
                file_path = os.path.join(UPLOAD_DIR, file.filename)
                with open(file_path, "wb") as buffer:
                    shutil.copyfileobj(file.file, buffer)
                saved_files.append(file_path)

            # TAHAP 2: Multiprocessing (CPU-Bound)
            yield f"data: {json.dumps({'step': 2, 'text': f'Tahap 2: Menjalankan Multiprocessing pada {len(saved_files)} file (Memanfaatkan Core CPU)...'})}\n\n"
            
            processed_output_paths = []
            loop = asyncio.get_running_loop()
            
            with ProcessPoolExecutor() as executor:
                futures = [
                    loop.run_in_executor(executor, process_single_image, f_path, PROCESSED_DIR)
                    for f_path in saved_files
                ]
                results = await asyncio.gather(*futures)
                
                for res in results:
                    if isinstance(res, dict) and res.get("status") == "success":
                        processed_output_paths.append(res["output"])

            # TAHAP 3: Multithreading (I/O-Bound)
            yield f"data: {json.dumps({'step': 3, 'text': 'Tahap 3: Menjalankan Multithreading untuk pengemasan Arsip ZIP...'})}\n\n"
            
            zip_filename = "batch_processed_images.zip"
            zip_filepath = os.path.join(PROCESSED_DIR, zip_filename)
            
            with ThreadPoolExecutor() as thread_executor:
                await loop.run_in_executor(thread_executor, create_zip_archive, processed_output_paths, zip_filepath)

            # SELESAI
            yield f"data: {json.dumps({'step': 4, 'text': 'Selesai! Semua proses berhasil dijalankan.', 'zip_filename': zip_filename})}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'step': -1, 'text': f'Error: {str(e)}'})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/download/{filename}")
async def download_file(filename: str):
    file_path = os.path.join(PROCESSED_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type='application/zip', filename=filename)
    return {"error": "File tidak ditemukan"}