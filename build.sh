#!/usr/bin/env bash
set -e

pip install -r requirements.txt

python -c "
import nltk
import ssl
try:
    ssl._create_default_https_context = ssl._create_unverified_context
except Exception:
    pass
nltk.download('punkt', quiet=True)
nltk.download('punkt_tab', quiet=True)
nltk.download('stopwords', quiet=True)
"
