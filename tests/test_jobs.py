import tempfile,unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.jobs import claim,enqueue,finish,get_job,work_once
from app.main import create_app
class JobsTests(unittest.TestCase):
    def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.db=Path(self.tmp.name)/'jobs.db'
    def tearDown(self):self.tmp.cleanup()
    def add(self,**kw):return enqueue(self.db,'word_count',{'text':'hello hello Python'},kw.pop('key','one'),now=0,**kw)[0]
    def test_success(self):
        job=self.add();work_once(self.db,now=0)
        self.assertEqual(get_job(self.db,job['id'])['result'],{'words':3,'unique_words':2})
    def test_retry_backoff(self):
        job=self.add(fail_first=True);work_once(self.db,now=0)
        self.assertEqual(get_job(self.db,job['id'])['status'],'queued')
        self.assertFalse(work_once(self.db,now=1));self.assertTrue(work_once(self.db,now=2))
        state=get_job(self.db,job['id']);self.assertEqual((state['status'],state['attempts']),('succeeded',2))
    def test_retry_limit(self):
        job=self.add()
        def fail(_):raise RuntimeError('Failure')
        for now in [0,2,6]:work_once(self.db,now=now,executor=fail)
        self.assertEqual(get_job(self.db,job['id'])['status'],'failed')
        self.assertFalse(work_once(self.db,now=100,executor=fail))
    def test_empty_exception_still_fails(self):
        job=self.add()
        def fail(_):raise RuntimeError()
        for now in [0,2,6]:work_once(self.db,now=now,executor=fail)
        self.assertEqual(get_job(self.db,job['id'])['status'],'failed')
    def test_duplicate_and_conflict(self):
        a=self.add();b=self.add();self.assertEqual(a['id'],b['id'])
        with self.assertRaises(ValueError):enqueue(self.db,'word_count',{'text':'changed'},'one',now=0)
    def test_claim_and_crash_recovery(self):
        self.add();first=claim(self.db,now=0);self.assertIsNone(claim(self.db,now=1))
        second=claim(self.db,now=31);self.assertEqual(second['attempts'],2)
        self.assertFalse(finish(self.db,first,result={'wrong':True},now=31))
        self.assertTrue(finish(self.db,second,result={'ok':True},now=32))
    def test_money_summary(self):
        job,_=enqueue(self.db,'sales_summary',{'amounts':[10.10,20.20]},'sales',now=0)
        work_once(self.db,now=0);self.assertEqual(get_job(self.db,job['id'])['result']['total'],'30.30')
    def test_invalid_input(self):
        for task,payload in [('bad',{}),('word_count',{'text':' '}),('sales_summary',{'amounts':[float('nan')]}),('sales_summary',{'amounts':[-1]}),('sales_summary',{'amounts':[True]})]:
            with self.assertRaises(ValueError):enqueue(self.db,task,payload,'test',now=0)
    def test_api(self):
        client=TestClient(create_app(self.db));self.assertEqual(client.get('/').status_code,200)
        response=client.post('/jobs',json={'task':'word_count','payload':{'text':'one two'},'request_key':'api'})
        self.assertEqual(response.status_code,202);job_id=response.json()['job']['id']
        work_once(self.db);self.assertEqual(client.get('/jobs/'+job_id).json()['status'],'succeeded')
        self.assertEqual(client.get('/jobs/missing').status_code,404)
if __name__=='__main__':unittest.main()
