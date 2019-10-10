#!/bin/bash

SECRETPATH="fireroad/secret.txt"
DBCREDPATH="fireroad/dbcreds.py"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installing dependencies
pip install django==1.11.15 pandas nltk lxml scipy scikit-learn requests pyjwt==1.6.4
echo
echo

# Secret key
if [ ! -f $SECRETPATH ]; then
  openssl rand -base64 80 > $SECRETPATH
  echo -e "${GREEN}Generated secret key at $SECRETPATH ${NC}"
fi

# Prompt for database type
BACKEND=$( python -c "from fireroad.settings import DATABASES; print(DATABASES['default']['ENGINE'])" )
NAME=$( python -c "from fireroad.settings import DATABASES; print(DATABASES['default']['NAME'])" )
read -p "You are set to use the database '$NAME' (backend: $BACKEND). Would you like to migrate to this backend? (y/n) " keepbackend
if [[ $keepbackend == "y" ]]; then
    # Migrate database
    echo "Migrating to database $NAME..."

    # Migrations
    python manage.py makemigrations common catalog courseupdater sync recommend requirements
    read -p "Ready to migrate? (y/n) " ready
    if [[ $ready != "y" ]]; then
      echo "Use the following command to migrate the database when ready:"
      echo
      echo "    python manage.py migrate"
      echo
      exit 0
    fi
    python manage.py migrate

    echo "Done migrating."
    exit 0
elif [[ $keepbackend == "n" ]]; then
    echo -e "${YELLOW}Please modify the fireroad/settings.py file to use the appropriate database, or specify a different settings module when running the server (such as settings_dev or settings_prod).${NC}"
else
  echo -e "${RED}Unrecognized symbol $keepbackend; quitting ${NC}"
  exit 1
fi


