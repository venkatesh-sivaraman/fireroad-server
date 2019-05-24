# FireRoad Server

FireRoad is an iOS/Android (and hopefully soon, web) application providing MIT students with accessible information about courses, subjects, and schedules. The FireRoad Server is a Django server that currently provides simple catalog auto-updating services but is intended to expand into course suggestion features later on.

The `master` branch of this repo is intended to be checked out and run by the production server. All changes not ready for `master` should be kept in the `develop` branch.

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

Note that we use SQLite for local testing and MySQL for production - you will need to comment/uncomment the appropriate settings in `fireroad/settings.py`. If the setup script detects you are using a MySQL database, it will walk you through the creation of a `fireroad/dbcreds.py` file that specifies the necessary authentication info.

To work with the login-based APIs, you will need a file at `recommend/oidc.txt` that contains two lines: one with the client ID and one with the client secret for the OAuth authorization server.

### Merging Notes

**Read this before you merge into master.** The develop and master branches contain different versions of `fireroad/settings.py`, which are critical for the different server behaviors in local development and production. To merge into master, try using the following to merge without modifying the settings file:

```
git merge --no-ff --no-commit <merge-branch>
git reset HEAD fireroad/settings.py
git checkout -- fireroad/settings.py
```

If you made any changes you want to keep in the settings file for production, you would need to redo those changes before committing the merge.

### API Endpoints

The FireRoad API is fully documented at [fireroad.mit.edu/reference](https://fireroad.mit.edu/reference) (dev version at [fireroad-dev.mit.edu/reference](https://fireroad-dev.mit.edu/reference)). When submitting PRs that modify the behavior of these endpoints or add new ones, please update the docs in `common/templates/docs` accordingly.
