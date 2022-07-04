init:
	pip install -r requirements.txt
run:
	python btmanager.py A4:C1:37:50:2C:2B
runrestart:
	timeout -k 10810 python btmanager.py A4:C1:37:50:2C:2B