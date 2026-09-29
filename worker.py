import argparse,logging,os,threading
from app.jobs import work_once
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--once',action='store_true');args=parser.parse_args()
    path=os.environ.get('JOBS_DB','data/jobs.db')
    logging.basicConfig(level=logging.INFO)
    if args.once:work_once(path)
    else:
        try:
            while True:
                if not work_once(path):threading.Event().wait(0.5)
        except KeyboardInterrupt:logging.info('Worker stopped')
