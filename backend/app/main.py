"""[5번 담당] FastAPI 앱

실행: (backend 폴더에서) uvicorn app.main:app --reload
확인: http://127.0.0.1:8000/docs
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.models import AnalyzeRequest, AnalyzeResponse
from app.pipeline import analyze

app = FastAPI(title="사기전에 API", version="0.1.0")

# 프론트엔드(다른 주소)에서 호출할 수 있게 허용 — 배포 시 실제 주소로 좁히기
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze_endpoint(req: AnalyzeRequest):
    return analyze(req.text)
