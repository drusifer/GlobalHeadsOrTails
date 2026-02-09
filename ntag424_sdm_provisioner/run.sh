. .venv/bin/activate && \
	env PYTHONPATH=/home/drusifer/Projects/GlobalHeadsOrTails/ntag424_sdm_provisioner/src:${PYTHON_PATH} \
	FLASK_APP=ntag424_sdm_provisioner.server.app \
	flask run --host=0.0.0.0 --port=5001 --debug --cert=adhoc
