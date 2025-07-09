#!/bin/bash

# Vytvoření potřebných složek
mkdir -p data output templates

# Instalace závislostí
pip install -r requirements.txt

# Spuštění aplikace
streamlit run app_new.py --server.port=$PORT --server.address=0.0.0.0 