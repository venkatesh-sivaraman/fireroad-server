# FireRoad Server

FireRoad is an iOS/Android application that allows MIT students to plan their course selections, view up-to-date major/minor requirements, and discover new courses. The FireRoad Server is a Django server that provides a data backend and document "cloud" for the native apps as well as the web-based CourseRoad application.

## Cloning and Setup

Follow these instructions to set up and run your own instance of the FireRoad server. You may want to create a new virtual environment using `conda`, for example:

```
conda create -n fireroad python=2.7
source activate fireroad
```

Then, enter the repo directory and run the setup script, which will install any necessary packages and set up the database.

```
$ cd fireroad-server
$ ./setup.sh
```

Note that the project contains three Django settings modules: `fireroad/settings.py` (local development), `fireroad/settings_dev.py` (dev server), and `fireroad_settings_prod.py` (prod server). When making changes to the settings, please make sure to change the file appropriate to the environment on which you want the changes to take effect (and note that the latter two import the base `settings.py` file). In order to specify which settings module should be used, you will need to set the `DJANGO_SETTINGS_MODULE` environment variable to `fireroad.settings{VARIANT}`, and change the default value specified in `fireroad/wsgi.py` if deploying with WSGI.

Depending on your settings, there may be additional files that you can add to enable certain capabilities:

* To use a MySQL database, add a `fireroad/dbcreds.py` file that specifies the necessary authentication info as Python variables `dbname`, `username`, `password`, and `host`.
* To enable sending emails to admins for unresolved edit requests, etc., create an email address with two-factor authentication disabled (gmail works well). Then add a `fireroad/email_creds.py` file that specifies authentication info as a comma-delimited string with three components: the email server (e.g. `smtp.gmail.com`), the email address, and the password for the email account.

### API Endpoints

The FireRoad API is fully documented at [fireroad.mit.edu/reference](https://fireroad.mit.edu/reference) (dev version at [fireroad-dev.mit.edu/reference](https://fireroad-dev.mit.edu/reference)). When submitting PRs that modify the behavior of these endpoints or add new ones, please update the docs in `common/templates/docs` accordingly.
