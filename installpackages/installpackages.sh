#!/bin/bash
# Linux install script for dbpSimulatorUI QGIS plugin
set -e

# Activate QGIS Python environment if needed
# source /path/to/qgis/python/env/bin/activate

# Install required Python packages
if [ -f requirements.txt ]; then
    pip install --user -r requirements.txt
else
    echo "requirements.txt not found."
    exit 1
fi

echo "Installation complete."

