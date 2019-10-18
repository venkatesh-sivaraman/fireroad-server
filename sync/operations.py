"""Implements core operations in the cloud sync module."""

import json
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from dateutil.parser import parse
from django.core.exceptions import ObjectDoesNotExist

from common.models import *
from .models import *

ANONYMOUS_AGENT = 'Anonymous'
NEW_FILE_ID = 1e30

### Sync Operations

class SyncResult:
    """Describes result states after a sync operation."""
    UPDATE_REMOTE = "update_remote"
    UPDATE_LOCAL = "update_local"
    CONFLICT = "conflict"
    NO_CHANGE = "no_change"

class SyncOperation(object):
    """A simple structure that represents a sync operation on a file, identified by its ID
    number."""

    def __init__(self, identifier, name, contents, change_date,
                 download_date, agent, override_conflict=False):
        """
        Creates a sync operation on a file with the given ID, name and contents.
        The change date should be a datetime at which the file was last
        modified by the agent; the download date indicates when the file was last
        downloaded by the agent; and the agent is a string describing the device
        on which the file was changed.
        """
        self.id = identifier
        self.name = name
        self.contents = contents
        self.change_date = change_date
        self.download_date = download_date
        self.agent = agent
        self.override_conflict = override_conflict

def sync(request, model_cls, operation):
    """
    Determines the sync state of the given model class when updating a file
    specified by the given operation (a SyncOperation instance). Returns a JSON-
    serializable dictionary indicating the final status of the sync.
    """
    # Get the remote version of the file
    if operation.id == NEW_FILE_ID:
        return add(request, model_cls, operation)

    try:
        remote_version = model_cls.objects.get(user=request.user, pk=operation.id)
    except ObjectDoesNotExist:
        # The object was deleted on the server, so present a conflict message
        if operation.override_conflict:
            return add(request, model_cls, operation)
        return conflict(model_cls, None, operation)

    if not has_conflict(model_cls, remote_version, operation):
        return {
            'success': True,
            'result': SyncResult.NO_CHANGE,
            'changed': remote_version.modified_date.isoformat()
        }

    # Compare the modification date of the remote version with the operation dates
    if operation.download_date is None:
        # It's an input error, since the client isn't adding a new file
        return {'success': False, 'error': 'You must provide a download date for existing files.'}

    if operation.download_date > operation.change_date:
        return {
            'success': False,
            'error': "The operation's change date should be after the download date."
        }
    if remote_version.modified_date <= operation.download_date:
        # Update the remote file
        return update_remote(model_cls, remote_version, operation)
    elif remote_version.modified_date >= operation.change_date:
        # The local's version is stale, send back the updated version
        return update_local(model_cls, remote_version, operation)
    else:
        # Conflict!
        if operation.override_conflict or operation.agent == remote_version.last_agent:
            return update_remote(model_cls, remote_version, operation)
        return conflict(model_cls, remote_version, operation)

def delete(request, model_cls, identifier):
    """Deletes the file with the given ID (in the primary-key field) from the
    given model class's database. Returns a JSON-style dictionary representing
    the result of the deletion."""
    try:
        model_file = model_cls.objects.get(user=request.user, pk=identifier)
    except ObjectDoesNotExist:
        return {'success': False, 'error': 'The file does not exist on the server.'}

    model_file.delete()
    return {'success': True, 'result': SyncResult.UPDATE_REMOTE}

def add(request, model_cls, operation):
    """Adds the file specified by the given SyncOperation to the given model
    database. Returns a JSON dictionary describing the result of the operation."""

    if not operation.name:
        return {
            'success': False,
            'error': 'You must provide a filename when adding a new file.'
        }
    if model_cls.objects.filter(user=request.user, name=operation.name).count() > 0:
        return {
            'success': False,
            'error_msg': 'The file already exists on the server. Please try again.'
        }

    try:
        contents = model_cls.compress(json.dumps(operation.contents))
    except: #pylint: disable=bare-except
        return {'success': False, 'error': 'Invalid contents JSON'}
    r = model_cls(user=request.user, name=operation.name, contents=contents)
    r.last_agent = operation.agent
    r.save()
    return {
        'success': True,
        'result': SyncResult.UPDATE_REMOTE,
        'changed': r.modified_date.isoformat(),
        'id': r.pk
    }

def update_remote(model_cls, file_to_update, operation):
    """Updates the given file according to the SyncOperation, and returns a
    JSON dictionary describing the result."""
    file_to_update.name = operation.name
    try:
        file_to_update.contents = model_cls.compress(json.dumps(operation.contents))
    except: #pylint: disable=bare-except
        return {'success': False, 'error': 'Invalid contents JSON'}
    file_to_update.last_agent = operation.agent
    file_to_update.save()
    return {
        'success': True,
        'result': SyncResult.UPDATE_REMOTE,
        'changed': file_to_update.modified_date.isoformat()
    }

def update_local(model_cls, file_to_update, operation):
    """Constructs and returns a JSON-style dictionary that indicates to the client
    to update its local version of the given file."""
    del operation
    return {
        'success': True,
        'result': SyncResult.UPDATE_LOCAL,
        'contents': json.loads(model_cls.expand(file_to_update.contents)),
        'name': file_to_update.name,
        'id': file_to_update.pk,
        'downloaded': timezone.now().isoformat(),
        'changed': file_to_update.modified_date.isoformat()
    }

def has_conflict(model_cls, file_to_check, operation):
    """Returns whether or not the remote file is in conflict with the new
    operation, content-wise."""
    if file_to_check.name != operation.name:
        return True
    try:
        return file_to_check.contents != model_cls.compress(json.dumps(operation.contents))
    except: #pylint: disable=bare-except
        return False

def conflict(model_cls, conflict_file, operation):
    """Constructs and returns a JSON-style dictionary that indicates the options
    for resolving the conflict between the file and the new operation."""
    if conflict_file is None:
        return {
            'success': True,
            'result': SyncResult.CONFLICT,
            'other_name': '',
            'other_agent': '',
            'other_date': '',
            'other_contents': '',
            'this_agent': operation.agent,
            'this_date': operation.change_date.isoformat()
        }
    return {
        'success': True,
        'result': SyncResult.CONFLICT,
        'other_agent': conflict_file.last_agent,
        'other_name': conflict_file.name,
        'other_date': conflict_file.modified_date.isoformat(),
        'other_contents': json.loads(model_cls.expand(conflict_file.contents)),
        'this_agent': operation.agent,
        'this_date': operation.change_date.isoformat()
    }

def browse(request, model_cls, file_id):
    """If file_id is None, returns a summary of all the files in the given model
    class's database. Otherwise, returns a JSON dictionary describing the given
    file ID."""
    if file_id is None:
        result = {}
        files = model_cls.objects.filter(user=request.user)
        for user_file in files:
            result[user_file.pk] = {
                'name': user_file.name,
                'changed': user_file.modified_date.isoformat(),
                'agent': user_file.last_agent
            }
        return {'success': True, 'files': result}

    try:
        user_file = model_cls.objects.get(user=request.user, pk=file_id)
    except ObjectDoesNotExist:
        resp = {'success': False, 'error_msg': 'The file was not found on the server.'}
        return resp

    try:
        contents = json.loads(model_cls.expand(user_file.contents))
    except: #pylint: disable=bare-except
        resp = {'success': False, 'error': 'The remote version of the file was invalid.'}
        return resp

    return {
        'success': True,
        'file': {
            'name': user_file.name,
            'id': user_file.pk,
            'changed': user_file.modified_date.isoformat(),
            'downloaded': timezone.now().isoformat(),
            'agent': user_file.last_agent,
            'contents': contents
        }
    }
