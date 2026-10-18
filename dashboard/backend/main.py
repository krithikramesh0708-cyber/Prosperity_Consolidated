from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from typing import Optional, List
import os
import json

from runner_api import run_custom_backtest, extract_zip_contents, process_data_package

app = FastAPI(title="Prosperity Backtest API")

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve the frontend
@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(os.path.dirname(__file__), "..", "frontend", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return f.read()
    return "<h1>Frontend index.html not found</h1>"

@app.post("/backtest")
async def backtest_endpoint(
    trader_file: UploadFile = File(...),
    data_files: List[UploadFile] = File(...),
    round_num: int = Form(2),
    day_num: int = Form(1)
):
    try:
        trader_code = (await trader_file.read()).decode("utf-8")
        
        # Collect all raw file contents (filename, content)
        all_files = []
        for upload in data_files:
            content = await upload.read()
            if upload.filename.endswith(".zip"):
                all_files.extend(extract_zip_contents(content))
            else:
                try:
                    all_files.append((upload.filename, content.decode("utf-8")))
                except UnicodeDecodeError:
                    continue # Ignore binary non-zip files
                    
        # Identify the relevant CSVs
        data_package = process_data_package(all_files)
        
        if not data_package["prices"]:
            raise HTTPException(status_code=400, detail="Could not find a valid prices CSV file in the uploads. Ensure it has 'prices' in the filename.")

        results = run_custom_backtest(
            trader_code=trader_code,
            data_package=data_package,
            round_num=round_num,
            day_num=day_num
        )
        
        # Add metadata about which files were found
        results["found_files"] = {k: v is not None for k, v in data_package.items()}
        
        return results
    except Exception as e:
        print(f"Error during backtest: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
