import time
from timeloop import Timeloop
from datetime import timedelta

tl = Timeloop()

def run_job():
    print ("5s job current time : {}",format(time.ctime()))


    
@tl.job(interval=timedelta(seconds=5))
def _job():
    run_job();
    
    
if __name__ == "__main__":
    tl.start(block=True)