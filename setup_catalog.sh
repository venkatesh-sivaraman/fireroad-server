#!/bin/bash

# This script handles setting up the catalog for local development.

GREEN='\033[0;32m'
NC='\033[0m' # No Color

CATALOG_DIR=$( python -c "from fireroad.settings import CATALOG_BASE_DIR; print(CATALOG_BASE_DIR)" )
if [ ! -d $CATALOG_DIR ]; then 
  echo "It looks like the course catalog directory is currently empty. You can download a copy (https://fireroad.mit.edu/courseupdater/download_data) and unzip it in the data directory."
  echo
  echo "Alternatively, you can begin without initial data using the instructions in data/readme.md."
  echo
  echo 

  read -p "Would you like to begin without initial data? (y/n) " ready
  if [[ $ready != "y" ]]; then
    echo "Run this script again after downloading and placing the catalog data."
    exit 0
  fi

  # Set up directories
  mkdir -p $CATALOG_DIR
  mkdir -p $CATALOG_DIR/raw
  mkdir -p $CATALOG_DIR/requirements
  mkdir -p $CATALOG_DIR/deltas
  mkdir -p $CATALOG_DIR/deltas/requirements

  echo "Done creating directories at $CATALOG_DIR. Follow the instructions in data/readme.md to run the catalog parser and create requirements lists."
fi

# Set location of settings file
export DJANGO_SETTINGS_MODULE="fireroad.settings"
echo -e "${GREEN}Running database update script...${NC}"
python update_db.py