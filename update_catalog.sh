#!/bin/bash

sentinel=$1/.update_sentinel
if [ -f "$sentinel" ]; then
  rm $sentinel
  source $2/../env/bin/activate
  python $2/update_catalog.py
fi
