from pathlib import Path
import tempfile
from typing import List
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from app.pipeline import PolicyLensPipeline

app = FastAPI(title="Policy Lens AI API", version="1.0.0", description="Evidence-grounded insurance policy assessment demo")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/assess")
async def assess_claim(question: str = Form(...), files: List[UploadFile] = File(...)):
    if not files:
        raise HTTPException(status_code=400, detail="Upload at least one policy document")
    paths = []
    with tempfile.TemporaryDirectory(prefix="policy_lens_") as folder:
        for f in files:
            safe_name = Path(f.filename or "policy.txt").name
            path = Path(folder) / safe_name
            path.write_bytes(await f.read())
            paths.append(str(path))
        try:
            pipeline = PolicyLensPipeline.from_paths(paths)
            result = pipeline.answer(question, top_k=5, use_llm=False)
            return result.to_dict()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
