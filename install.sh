#!/bin/bash

# Use this script with sudo or su

# Go to home user
cd ~

# Install dependencies
apt install python3-pip python3-venv -y

# Make directory for venv
mkdir ovh

# Go to venv hosting folder
cd ovh

# Create venv
python3 -m venv getOVHbills

# Activate venv
source getOVHbills/bin/activate

# Get pip dependencies
pip install ovh requests

# Give execution rights to the script
chmod +x ~/getOVHbills.py

# Move script in the venv hosting folder
mv ~/getOVHbills.py ~/ovh/

# WARNING: Please edit this line before executing the script to fit your situation
crontab -l|sed "\$a0 0 15 * * /your/folder/ovh/getOVHbills/bin/python3 /your/folder/ovh/getOVHbills.py >> /your/folder/ovh/getOVHbills.log 2>&1"|crontab -
