#!/bin/bash

SECRETPATH="fireroad/secret.txt"
DBCREDPATH="fireroad/dbcreds.py"
DEFAULT_CATALOGPATH="$( pwd )/catalog_files"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Installing dependencies
pip install django==1.11.15 pandas nltk lxml scipy scikit-learn requests pyjwt==1.6.4
python -m nltk.downloader popular
echo
echo

# Secret key
if [ ! -f $SECRETPATH ]; then
  openssl rand -base64 80 > $SECRETPATH
  echo -e "${GREEN}Generated secret key at $SECRETPATH ${NC}"
fi

# Check for database credentials, if applicable
hasdbcreds=$( python -c 'try:
  import fireroad.settings
  print("y")
except:
  try:
    import dbcreds
    print("y")
  except:
    print("n")
' )
if [[ $hasdbcreds == "n" ]]; then
  echo -e "${YELLOW}The fireroad/settings.py module requires database credentials to use MySQL.${NC}"
  read -p "Press Enter to add these credentials, or press ^C to quit and change the database backend in fireroad/settings.py." continue
  read -p "Enter the host URL for the database (e.g. sql.mit.edu): " host
  read -p "Enter the database name: " dbname
  read -p "Enter the username to log into the database: " username
  read -p "Enter the password: " -s passwd
  echo

  echo 'dbname = "'$dbname'"
username = "'$username'"
password = "'$passwd'"
host = "'$host'"' > $DBCREDPATH
  echo -e "${GREEN}Wrote database credentials to $DBCREDPATH. ${NC}"
fi

# Prompt for database type
BACKEND=$( python -c "from fireroad.settings import DATABASES; print(DATABASES['default']['ENGINE'])" )
NAME=$( python -c "from fireroad.settings import DATABASES; print(DATABASES['default']['NAME'])" )
read -p "You are set to use the database '$NAME' (backend: $BACKEND). Would you like to continue using this backend? (y/n) " keepbackend
if [[ $keepbackend == "n" ]]; then
  echo -e "${YELLOW}Please modify the fireroad/settings.py file to use the appropriate database.${NC}"
  exit 0
elif [[ $keepbackend != "y" ]]; then
  echo -e "${RED}Unrecognized symbol $keepbackend; quitting ${NC}"
  exit 1
fi

echo
echo

# Migrate database
echo "Migrating to database $NAME..."

# Migrations
python manage.py makemigrations common catalog courseupdater sync recommend requirements analytics
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

# Catalog files

echo
echo -e "${YELLOW}FireRoad uses catalog files to store information about the course catalog and major/minor requirements.${NC}"
read -p "Press Enter to use the default path ($DEFAULT_CATALOGPATH) or type a new catalog path: " catalogpath
if [ -z "$catalogpath" ]; then
  catalogpath=$DEFAULT_CATALOGPATH
fi
echo "Editing fireroad/settings.py to point to your desired catalog base directory. Please do not commit this change."
sed -i.bak "s:CATALOG_BASE_DIR = .*$:CATALOG_BASE_DIR = \""${catalogpath}"\":g" fireroad/settings.py

mkdir -p $catalogpath 
mkdir -p $catalogpath/deltas
mkdir -p $catalogpath/raw

echo "Done configuring catalog files."
read -p "Would you like to populate the database with an initial set of catalog data? (y/n) " dbrun
if [[ $dbrun == "n" ]]; then
  echo -e "You can setup the database later by running python update_catalog.py fall-2019 (replace with the current semester), then python delta_gen.py, then python update_db.py."
  exit 0
elif [[ $dbrun != "y" ]]; then
  echo -e "${RED}Unrecognized symbol $dbrun; quitting ${NC}"
  exit 1
fi

echo

# Run the catalog updater
read -p "Enter the current semester in the form SEASON-YEAR (e.g. fall-2019): " semester
python update_catalog.py $semester || exit 1
python catalog_parse/delta_gen.py $catalogpath/sem-$semester-new $catalogpath/sem-$semester $catalogpath/deltas || exit 1
python update_db.py || exit 1
echo -e "${GREEN}Finished populating database!${NC}"
echo "You can add requirements later by adding them to $catalogpath/requirements, then running update_db.py again."
