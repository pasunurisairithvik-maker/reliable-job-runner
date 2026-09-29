"""A persistent queue for two bounded, deterministic tasks; no arbitrary code execution."""
import json
import sqlite3
import time
import uuid
from pathlib import Path
from decimal import Decimal

MAX_ATTEMPTS=3
LEASE_SECONDS=30


def connect(path):
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(path,timeout=10);con.row_factory=sqlite3.Row
    con.execute("PRAGMA busy_timeout=10000")
    con.execute("""CREATE TABLE IF NOT EXISTS jobs (
        id TEXT PRIMARY KEY, request_key TEXT UNIQUE NOT NULL,
        task TEXT NOT NULL, payload TEXT NOT NULL,
        fail_first INTEGER NOT NULL, status TEXT NOT NULL,
        attempts INTEGER NOT NULL DEFAULT 0,
        available_at REAL NOT NULL, lease_until REAL,
        claim_token TEXT, result TEXT, error TEXT,
        created_at REAL NOT NULL, updated_at REAL NOT NULL)""")
    con.execute("CREATE INDEX IF NOT EXISTS ready_jobs ON jobs(status,available_at)")
    con.commit();return con


def validate(task,payload):
    if task=='word_count':
        if set(payload)!={'text'} or not isinstance(payload['text'],str) or not payload['text'].strip() or len(payload['text'])>10000:
            raise ValueError('word_count needs nonblank text of at most 10000 characters')
    elif task=='sales_summary':
        values=payload.get('amounts')
        if set(payload)!={'amounts'} or not isinstance(values,list) or not 1<=len(values)<=1000:
            raise ValueError('sales_summary needs 1-1000 amounts')
        for value in values:
            if isinstance(value,bool) or not isinstance(value,(int,float)):
                raise ValueError('Amounts must be finite nonnegative numbers with up to two decimals')
            amount=Decimal(str(value))
            if not amount.is_finite() or not 0<=amount<=1000000000 or amount!=amount.quantize(Decimal('.01')):
                raise ValueError('Amounts must be finite nonnegative numbers with up to two decimals')
    else: raise ValueError('Unknown task')


def public(row):
    if row is None: return None
    data=dict(row)
    for field in ['claim_token','lease_until','payload','request_key','fail_first']:data.pop(field,None)
    data['result']=json.loads(data['result']) if data['result'] else None
    return data


def get_job(path,job_id):
    con=connect(path)
    try:return public(con.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone())
    finally:con.close()


def enqueue(path,task,payload,request_key,fail_first=False,now=None):
    validate(task,payload)
    if not isinstance(request_key,str) or not 1<=len(request_key)<=100:raise ValueError('request_key needs 1-100 characters')
    now=time.time() if now is None else now
    encoded=json.dumps(payload,sort_keys=True,allow_nan=False)
    con=connect(path)
    try:
        con.execute('BEGIN IMMEDIATE')
        existing=con.execute('SELECT * FROM jobs WHERE request_key=?',(request_key,)).fetchone()
        if existing:
            if (existing['task'],existing['payload'],existing['fail_first'])!=(task,encoded,int(fail_first)):
                raise ValueError('request_key already belongs to a different request')
            con.commit();return public(existing),False
        job_id=str(uuid.uuid4())
        con.execute("INSERT INTO jobs (id,request_key,task,payload,fail_first,status,available_at,created_at,updated_at) VALUES (?,?,?,?,?,'queued',?,?,?)",(job_id,request_key,task,encoded,int(fail_first),now,now,now))
        con.commit();return get_job(path,job_id),True
    except Exception:
        con.rollback();raise
    finally:con.close()


def claim(path,now=None):
    now=time.time() if now is None else now
    con=connect(path)
    try:
        con.execute('BEGIN IMMEDIATE')
        # A crashed worker leaves a lease. Recovery is at-least-once execution.
        con.execute("UPDATE jobs SET status=CASE WHEN attempts>=? THEN 'failed' ELSE 'queued' END, lease_until=NULL, claim_token=NULL, error='Worker lease expired', updated_at=? WHERE status='running' AND lease_until<=?",(MAX_ATTEMPTS,now,now))
        row=con.execute("SELECT * FROM jobs WHERE status='queued' AND available_at<=? ORDER BY created_at,id LIMIT 1",(now,)).fetchone()
        if row is None:con.commit();return None
        token=str(uuid.uuid4())
        con.execute("UPDATE jobs SET status='running',attempts=attempts+1,lease_until=?,claim_token=?,updated_at=? WHERE id=?",(now+LEASE_SECONDS,token,now,row['id']))
        result=con.execute('SELECT * FROM jobs WHERE id=?',(row['id'],)).fetchone()
        con.commit();return dict(result)
    except Exception:con.rollback();raise
    finally:con.close()


def execute(job):
    if job['fail_first'] and job['attempts']==1:raise RuntimeError('Simulated temporary failure')
    payload=json.loads(job['payload'])
    if job['task']=='word_count':
        words=payload['text'].split()
        return {'words':len(words),'unique_words':len({w.casefold() for w in words})}
    values=[Decimal(str(value)) for value in payload['amounts']]
    total=sum(values,Decimal(0))
    return {'orders':len(values),'total':str(total.quantize(Decimal('.01'))),'average':str((total/len(values)).quantize(Decimal('.01')))}


def finish(path,job,result=None,error=None,now=None):
    now=time.time() if now is None else now
    retry=error is not None and job['attempts']<MAX_ATTEMPTS
    status='queued' if retry else ('failed' if error else 'succeeded')
    next_time=now+2**job['attempts'] if retry else now
    con=connect(path)
    try:
        with con:
            updated=con.execute("UPDATE jobs SET status=?,available_at=?,lease_until=NULL,claim_token=NULL,result=?,error=?,updated_at=? WHERE id=? AND status='running' AND claim_token=?",(status,next_time,json.dumps(result) if result is not None else None,error,now,job['id'],job['claim_token']))
            return updated.rowcount==1
    finally:con.close()


def work_once(path,now=None,executor=execute):
    job=claim(path,now)
    if not job:return False
    try:result=executor(job)
    except Exception as exc:finish(path,job,error=str(exc),now=now)
    else:finish(path,job,result=result,now=now)
    return True
