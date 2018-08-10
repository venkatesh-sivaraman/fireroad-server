# FireRoad Server

FireRoad is an iOS (and hopefully soon, web) application providing MIT students with accessible information about courses, subjects, and schedules. The FireRoad Server is a Django server that currently provides simple catalog auto-updating services but is intended to expand into course suggestion features later on.

The `master` branch of this repo is intended to be checked out and run by the production server. All changes not ready for `master` should be kept in the `develop` branch.

## Setup

Once you have checked out the repo, you will need to generate a secret key, for example:

```
$ cd fireroad
$ openssl rand -base64 80 > fireroad/secret.txt
```

You will then need to create a file called `dbcreds.py` within the (inner) `fireroad` directory that defines the following variables: `dbname`, `username`, `password`, and `host`. These are used to initialize the MySQL database in `settings.py`.

Finally, you will need a file at `recommend/oidc.txt` that contains two lines: one with the client ID and one with the client secret for the OAuth authorization server.

## API Endpoints

*(Up-to-date as of 8/10/2018)* All endpoints in `recommend` and `sync` require login.

### Authentication

* `/signup/`: Displays a user-facing page that specifies the conditions of allowing recommendations.

* `/login/`: Redirects to the OAuth page (URL specified in `common/oauth_client.py`) to log the user in.

* `/verify/` *(GET)*: Checks that the user is logged in, and if so, auto-increments the user's current semester and returns the new semester.

### Course Updater

* `/courseupdater/semesters/` *(GET)*: Returns a JSON list specifying the order of the semesters available on the server, as well as their current version numbers.

* `/courseupdater/check/` *(GET)*: Given a semester and local version number, returns a new version number and the delta of catalog files that should be updated. Takes as query parameters:

  * `sem`, a comma-separated specification of the semester (e.g. "fall,2018")
  * `v`, the local version number of the catalog

### Recommender

* `/recommend/rate/` *(POST)*: The body of the request should be a JSON list of dictionaries, each containing `s` (subject ID) and `v` (rating value). Updates the ratings for each item.

* `/recommend/get/` *(GET)*: Takes an optional parameter `t` indicating the type of recommendation to return. Returns a dictionary of recommendation types mapped to JSON strings indicating the recommended subjects and their rating values.

### Sync

* `/sync/roads/` *(GET)*: If a primary key is specified by the `id` query parameter, returns the contents of the given file as well as its last-modified agent. If no primary key is specified, returns a dictionary of primary-keys to metadata about each of the user's roads.

* `/sync/sync_road/` *(POST)*: This endpoint determines whether to change the remote copy of the file, update the local copy, or handle a sync conflict. The body of the request should be a JSON dictionary containing the following keys:

  * `id`: The primary key of the road to update (don't pass if adding a new file)
  * `contents`: The contents of the road to update
  * `changed`: The local last-modified date of the road
  * `downloaded`: The date of the last download of the road from the server
  * `name`: The road name (required if adding a new file, or if renaming an existing road)
  * `agent`: The name of the device submitting the change
  * `override`: Whether to override conflicts

  Returns a JSON dictionary that may update the above keys and/or add the following keys:

  * `success`: Whether the file was successfully compared against its remote version
  * `error`: A console error if `success` is false
  * `error_msg`: A user-facing error to display if `success` is false
  * `result`: A string indicating the result of the operation, e.g. "update_remote", "update_local", "conflict", or "no_change"
  * `other_name`, `other_agent`, `other_date`, `other_contents`, `this_agent`, `this_date`: Keys that are specified in the case of a conflict. In this case, the user should select whether to keep the local copy, the remote copy, or both. If keeping the local copy, the client should submit a new `sync_road` request with the `override` flag set to true.

* `/sync/delete_road/` *(POST)*: Deletes the file specified by the `id` key in the body of the request.
