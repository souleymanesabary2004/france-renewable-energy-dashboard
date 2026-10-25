# Simple run instructions (on Windows without make, use the plain commands from README.md)
PY ?= python

.PHONY: setup data app test notebooks zip clean

setup:            ## create the environment (once)
	$(PY) -m venv .venv && . .venv/bin/activate && pip install -r requirements-dev.txt

data:             ## download the raw file (cached) and rebuild every processed table
	$(PY) -m utils.io build

app:              ## run the dashboard
	streamlit run app.py

test:             ## unit tests of the pipeline and of the aggregations
	$(PY) -m pytest -q tests

notebooks:        ## re-run notebooks 02 and 03 (01 needs the raw file at data/)
	jupyter nbconvert --to notebook --execute --inplace notebooks/02_cleaning_feature_engineering.ipynb
	jupyter nbconvert --to notebook --execute --inplace notebooks/03_eda_storytelling.ipynb

zip:              ## build the submission zip: make zip NUM=20000 NAME=SOUMAHORO GROUP=DE1
	$(PY) scripts/make_zip.py --number $(NUM) --name $(NAME) --group $(GROUP)

clean:
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
