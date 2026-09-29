import os
import sqlite3
from pathlib import Path
from fastapi import FastAPI,HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from app.jobs import enqueue,get_job

class JobRequest(BaseModel):
    task:str
    payload:dict
    request_key:str=Field(min_length=1,max_length=100)
    fail_first:bool=False

def create_app(path=None):
    api=FastAPI(title='Reliable Job Runner')
    db=path or os.environ.get('JOBS_DB','data/jobs.db')
    @api.get('/',response_class=HTMLResponse)
    def home():return (Path(__file__).parent/'index.html').read_text()
    @api.post('/jobs',status_code=202)
    def submit(request:JobRequest):
        try:
            job,created=enqueue(db,request.task,request.payload,request.request_key,request.fail_first)
            return {'created':created,'job':job}
        except ValueError as exc:raise HTTPException(400,str(exc)) from exc
        except sqlite3.Error as exc:raise HTTPException(503,'Database unavailable') from exc
    @api.get('/jobs/{job_id}')
    def status(job_id:str):
        try:job=get_job(db,job_id)
        except sqlite3.Error as exc:raise HTTPException(503,'Database unavailable') from exc
        if job is None:raise HTTPException(404,'Job not found')
        return job
    return api
app=create_app()
