from fastapi import FastAPI
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from Router import jobResume, resumeDiagnosis, interview, careerPlan, ocr
from Router import careerPlan

load_dotenv()

app = FastAPI(title="一站式AI职业生涯导航员")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobResume.router)
app.include_router(resumeDiagnosis.router)
app.include_router(interview.router)
app.include_router(careerPlan.router)
app.include_router(ocr.router, prefix="/api/ocr", tags=["OCR"])

