#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."
python -c 'import sys; assert sys.version_info[:2] == (3,10), "Activate a Python 3.10 environment first"'
python -m pip install 'pip==24.2' 'setuptools==69.5.1' 'wheel==0.44.0'
python -m pip install 'torch==2.4.1' 'torchvision==0.19.1' --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r requirements-bc-a100.txt
python -m pip install --no-deps -e .
python -m pip check
mkdir -p logs
python -m pip freeze > logs/bc-installed-packages.txt
printf '%s\n' 'BC environment installed. Next: python scripts/run_handoff_experiment.py --stage smoke'
