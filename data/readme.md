# FireRoad Catalog Data

FireRoad's functionality depends on managing an up-to-date data source for both course catalogs and requirements. This data is expected to be located in the directory named in the settings file (`fireroad.settings` for local testing, `fireroad.settings_dev` for the dev server, and `fireroad.settings_prod` for the prod server). You can obtain an up-to-date copy of the data through the Django admin menu on either deployed service.

The catalog data is structured this way (in addition to the database model) for ease of managing specific files corresponding to catalogs or requirements lists; also, the files are statically served for the mobile apps.

## Structure

The catalogs directory should be structured as follows:

```
- requirements
   - major1.reql
   - ...
- sem-fall-2019
   - 1.txt
   - ...
- sem-spring-2020
   - 1.txt
   - ...
- ...
- raw
   - sem-spring-2020
      - 1.txt
      - ...
   - ...
- deltas
   - requirements
      - delta-1.txt
      - ...
   - sem-fall-2019
      - delta-1.txt
      - ...
   - sem-spring-2020
      - delta-1.txt
      - ...
```

The top-level directories contain the data files for `requirements` and semesters (prefixed by `sem-`). The `raw` directory contains intermediate files generated during catalog parse operations (see below). The `deltas` directory contains a directory named for each of those top-level directories, which contains the delta files for each version of the catalog. 

Each delta file is named `delta-[VERSION-NUMBER].txt` and formatted as follows (filenames are listed without extension):

```
[SEASON]#,#[YEAR]
[VERSION NUMBER]
[CHANGED FILENAME 1]
[CHANGED FILENAME 2]
...
```

## Update Scripts

The course catalog update process is automated and can largely be managed through the web interface. However, because this is a singleton process that must occur outside a single server-client connection, it relies on the external script `update_catalog.py`, which is run as a cron job every few minutes on deployed servers. Similarly, the `update_db.py` script is scheduled to run daily during the early morning, to avoid performing database tasks during normal usage hours.

You can run these scripts manually in the command line as well. First, set the `DJANGO_SETTINGS_MODULE` environment variable in your terminal:

```
export DJANGO_SETTINGS_MODULE="fireroad.settings"
```

Then, run the script as directed below.

### Catalog Updates

 On a local version, you can easily start this script manually by the command

```
python update_catalog.py [SEASON]-[YEAR]
```

where `[SEASON]-[YEAR]` specifies the current semester (e.g. `fall-2020`). Once this script is started, you can navigate to the catalog update page in the UI to watch the progress and review the results. When it is finished, you will need to click Deploy Update. Finally, run the database update script:

```
python update_db.py
```

Note that each of these scripts may take several minutes to run.

### Requirements Updates

Requirements list updating follows a similar process to the course catalog, except that updates are entered manually instead of scraped. Therefore, you can edit the requirements lists directly in the Requirements Editor, deploy them, and then run the database update script:

```
python update_db.py
```