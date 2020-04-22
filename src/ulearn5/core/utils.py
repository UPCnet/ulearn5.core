# -*- coding: utf-8 -*-
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from Products.Five.browser import BrowserView

from datetime import timedelta
from plone import api
from plone.event.interfaces import IEventAccessor
from plone.event.utils import is_datetime
from plone.event.utils import is_date
from plone.registry.interfaces import IRegistry
from repoze.catalog.query import Eq
from souper.soup import get_soup
from zope import schema
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.component import getMultiAdapter
from zope.contentprovider.interfaces import IContentProvider

from mrs5.max.utilities import IMAXClient
from ulearn5.core import _
from ulearn5.core.controlpanel import IUlearnControlPanelSettings

import json
import pytz
import re
import transaction

RE_VALID_TWITTER_USERNAME = r'^\s*@?([a-zA-Z0-9_]{1,15})\s*$'


class InvalidTwitterUsernameError(schema.ValidationError):
    __doc__ = _(u"Invalid twitter username.")


def isValidTwitterUsername(text):
    """
        Is a valid twitter username?
        See max.regex for more info on the regex
    """
    match = re.match(RE_VALID_TWITTER_USERNAME, text)
    success = match is not None
    if not success:
        raise InvalidTwitterUsernameError
    else:
        return True


def stripTwitterUsername(text):
    """
        Returns the valid part of a twitter username input, lowercased
    """
    return re.sub(RE_VALID_TWITTER_USERNAME, r'\1', text).lower()


def json_response(func):
    """ Decorator to transform the result of the decorated function to json.
        Expect a list (collection) that it's returned as is with response 200 or
        a dict with 'data' and 'status_code' as keys that gets extracted and
        applied the response.
    """
    def decorator(*args, **kwargs):
        instance = args[0]
        request = getattr(instance, 'request', None)
        request.response.setHeader(
            'Content-Type',
            'application/json; charset=utf-8'
        )
        result = func(*args, **kwargs)
        if isinstance(result, list):
            request.response.setStatus(200)
            return json.dumps(result, indent=2, sort_keys=True)
        else:
            request.response.setStatus(result.get('status_code', 200))
            return json.dumps(result.get('data', result), indent=2, sort_keys=True)

    return decorator


def is_activate_owncloud(self):
    """ Returns True id ulearn5.owncloud is installed """
    return isInstalledProduct(self, 'ulearn5.owncloud')

def is_activate_externalstorage(self):
    """ Returns True id ulearn5.externalstorage is installed """
    return isInstalledProduct(self, 'ulearn5.externalstorage')

class ulearnUtils(BrowserView):
    """ Convenience methods placeholder ulearn.utils view. """

    def portal(self):
        return api.portal.get()

    def get_url_forget_password(self, context):
        """ return redirect url when forget user password """
        portal = getToolByName(context, 'portal_url').getPortalObject()
        base_path = '/'.join(portal.getPhysicalPath())
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings)
        if 'http' in settings.url_forget_password:
            return settings.url_forget_password
        else:
            return base_path + settings.url_forget_password

    def is_angularview(self):
        if IPloneSiteRoot.providedBy(self.context):
            return None
        else:
            return ''

    def is_siteroot(self):
        if IPloneSiteRoot.providedBy(self.context):
            return True
        else:
            return False

    def url_max_server(self):
        self.maxclient, self.settings = getUtility(IMAXClient)()
        return self.settings.max_server


    def is_activate_sharedwithme(self):
        if (api.portal.get_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.elasticsearch') != None) and (api.portal.get_registry_record('ulearn5.core.controlpanel.IUlearnControlPanelSettings.activate_sharedwithme') == True):
            portal = api.portal.get()
            if portal.portal_actions.object.local_roles.visible == False:
                portal.portal_actions.object.local_roles.visible = True
                transaction.commit()
            return True
        else:
            return False

    def is_activate_news(self):
        if api.portal.get_registry_record('ulearn5.core.controlpanel.IUlearnControlPanelSettings.activate_news') == True:
            return True
        else:
            return False


    def formatted_date_user_timezone(self, occ):
        provider = getMultiAdapter(
            (self.context, self.request, self),
            IContentProvider, name='formatted_date_user_timezone'
        )
        return provider(occ)

def isInstalledProduct(self, package):
    qi = getToolByName(self, 'portal_quickinstaller')
    prods = qi.listInstalledProducts()
    for prod in prods:
        if prod['id'] == package:
            return True
    return False


def getSearchersFromUser():
    portal = getSite()
    current_user = api.user.get_current()
    userid = current_user.id
    soup_searches = get_soup('user_news_searches', portal)
    exist = [r for r in soup_searches.query(Eq('id', userid))]

    res = []
    if exist:
        values = exist[0].attrs['searches']
        if values:
            for val in values:
                res.append(' '.join(val))
    return res


def getUserPytzTimezone():
    """If the user does not have a timezone, the default portal is used.
    """
    timezone = api.user.get_current().getProperty('timezone', '')
    if not timezone:
        timezone = api.portal.get_registry_record('plone.portal_timezone')

    return pytz.timezone(timezone)


def construct_calendar_user_timezone(events, start=None, end=None):
    """Return a dictionary with dates in a given timeframe as keys and the
    actual occurrences for that date for building calendars.
    Long lasting events will occur on every day until their end.

    :param events: List of IEvent and/or IOccurrence objects, to construct a
                   calendar data structure from.
    :type events: list

    :param start: An optional start range date.
    :type start: Python datetime or date

    :param end: An optional start range date.
    :type end: Python datetime or date

    :returns: Dictionary with isoformat date strings as keys and event
              occurrences as values.
    :rtype: dict

    """
    if start:
        if is_datetime(start):
            start = start.date()
        assert is_date(start)
    if end:
        if is_datetime(end):
            end = end.date()
        assert is_date(end)

    cal = {}

    def _add_to_cal(cal_data, event, date):
        date_str = date.isoformat()
        if date_str not in cal_data:
            cal_data[date_str] = [event]
        else:
            cal_data[date_str].append(event)
        return cal_data

    timezone = getUserPytzTimezone()
    for event in events:
        acc = IEventAccessor(event)
        start_date = acc.start.astimezone(timezone).date()
        end_date = acc.end.astimezone(timezone).date()

        # day span between start and end + 1 for the initial date
        range_days = (end_date - start_date).days + 1
        for add_day in range(range_days):
            next_start_date = start_date + timedelta(add_day)  # initial = 0

            # avoid long loops
            if start and end_date < start:
                break  # if the date is completly outside the range
            if start and next_start_date < start:
                continue  # if start_date is outside but end reaches into range
            if end and next_start_date > end:
                break  # if date is outside range

            _add_to_cal(cal, event, next_start_date)
    return cal
