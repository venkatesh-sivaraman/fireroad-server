#!/bin/bash

sentinel=${BASH_SOURCE%/*}/courseupdater/.update_sentinel
if [ -f "$sentinel" ]; then
  rm sentinel
  source ${BASH_SOURCE%/*}/../env/bin/activate
  python update_catalog.py
fi
