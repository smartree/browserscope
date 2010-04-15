#!/usr/bin/python2.5
#
# Copyright 2009 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Shared decorators."""

__author__ = 'elsigh@google.com (Lindsey Simon)'

import hashlib
import logging
import random

from google.appengine.api import users

from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import HttpResponseForbidden

import settings


def admin_required(func):
  """Tests to make sure the current user is an admin."""
  def _wrapper(request, *args, **kw):
    user = users.get_current_user()
    if user:
      if users.is_current_user_admin():
        return func(request, *args, **kw)
      else:
        return HttpResponse('You need to be an admin. <a href="%s">login</a>.'
                            % users.create_login_url(request.get_full_path()))
    else:
      return HttpResponseRedirect(
          users.create_login_url(request.get_full_path()))
  return _wrapper



def dev_appserver_only(func):
  def _wrapper(request, *args, **kw):
    if settings.BUILD == 'production':
      return HttpResponse('Only for dev_appserver eyes.')
    return func(request, *args, **kw)
  return _wrapper


_MAX_CSRF_KEY = 18446744073709551616L
def _make_csrf_key():
  # Use the system (hardware-based) random number generator if it exists.
  if hasattr(random, 'SystemRandom'):
    randrange = random.SystemRandom().randrange
  else:
 	  randrange = random.randrange
  csrf_key = hashlib.md5('%s%s' % (randrange(0, _MAX_CSRF_KEY),
                                   settings.SECRET_KEY)
                         ).hexdigest()
  return csrf_key


def provide_csrf(func):
  """Inserts a csrf_token into request.session's list of valid tokens."""
  def _wrapper(request, *args, **kw):
    csrf_token = _make_csrf_key()
    try:
      request.session['csrf_tokens'].append(csrf_token)
    except:
      request.session['csrf_tokens'] = [csrf_token]

    # Expose a single token for session handlers.
    request.session['csrf_token'] = csrf_token

    return func(request, *args, **kw)
  return _wrapper


def check_csrf(func):
  """Checks/removes a csrf_token from request.session's list of valid tokens."""
  def _wrapper(request, *args, **kw):
    valid_csrf_tokens = request.session.get('csrf_tokens')
    request_csrf_token = request.REQUEST.get('csrf_token')

    if request_csrf_token is None:
      return HttpResponseForbidden('CSRF Error - Need csrf_token in request.')
    if valid_csrf_tokens is None or request_csrf_token not in valid_csrf_tokens:
      return HttpResponseForbidden('CSRF Error - Invalid csrf_token.')

    request.session['csrf_token'] = None
    request.session['csrf_tokens'].remove(request_csrf_token)

    return func(request, *args, **kw)
  return _wrapper


def provide_check_csrf(func):
  def _wrapper(request, *args, **kw):
    if request.POST:
      #return check_csrf._wrapper(request, *args, **kw)
      return func(request, *args, **kw)
    else:
      #return provide_csrf._wrapper(request, *args, **kw)
      return func(request, *args, **kw)
  return _wrapper