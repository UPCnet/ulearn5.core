# -*- coding: utf-8 -*-
import json
import pytz
import re
import transaction

from bs4.element import Tag, NavigableString
from bs4 import BeautifulSoup
from datetime import timedelta
from time import time

from Acquisition import aq_inner
from Products.CMFPlone.interfaces.siteroot import IPloneSiteRoot
from Products.Five.browser import BrowserView

from plone import api
from plone.app.layout.navigation.root import getNavigationRootObject
from plone.event.interfaces import IEventAccessor
from plone.event.utils import is_datetime
from plone.event.utils import is_date
from plone.memoize import ram
from plone.registry.interfaces import IRegistry
from repoze.catalog.query import Eq
from souper.interfaces import ICatalogFactory
from souper.soup import get_soup
from zope import schema
from zope.component import getUtility
from zope.component import queryUtility
from zope.component import getMultiAdapter
from zope.component import getUtilitiesFor
from zope.component.hooks import getSite
from zope.contentprovider.interfaces import IContentProvider

from mrs5.max.utilities import IMAXClient
from base5.core.directory import METADATA_USER_ATTRS
from ulearn5.core import _
from ulearn5.core.content.community import ICommunity
from ulearn5.core.controlpanel import IUlearnControlPanelSettings


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


@ram.cache(lambda *args: time() // (60 * 60))
def packages_installed():
    qi_tool = api.portal.get_tool(name='portal_quickinstaller')
    installed = [p['id'] for p in qi_tool.listInstalledProducts()]
    return installed


def is_activate_owncloud(self):
    """ Returns True id ulearn5.owncloud is installed """
    installed = packages_installed()
    if 'ulearn5.owncloud' in installed:
        return True
    return False


def is_activate_externalstorage(self):
    """ Returns True id ulearn5.externalstorage is installed """
    installed = packages_installed()
    if 'ulearn5.externalstorage' in installed:
        return True
    return False


def is_activate_etherpad(self):
    """ Returns True id ulearn5.etherpad is installed """
    installed = packages_installed()
    if 'ulearn5.etherpad' in installed:
        return True
    return False


class ulearnUtils(BrowserView):
    """ Convenience methods placeholder ulearn.utils view. """

    def portal(self):
        return api.portal.get()

    def get_url_forget_password(self, context):
        """ return redirect url when forget user password """
        portal = api.portal.get_tool(name='portal_url').getPortalObject()
        registry = queryUtility(IRegistry)
        settings = registry.forInterface(IUlearnControlPanelSettings)
        if 'http' in settings.url_forget_password:
            return settings.url_forget_password
        else:
            return portal.absolute_url() + settings.url_forget_password

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
        if api.portal.get_registry_record('ulearn5.core.controlpanel.IUlearnControlPanelSettings.activate_news') is True:
            return True
        else:
            return False

    def formatted_date_user_timezone(self, occ):
        provider = getMultiAdapter(
            (self.context, self.request, self),
            IContentProvider, name='formatted_date_user_timezone'
        )
        return provider(occ)

    def user_id(self):
        portal_state = getMultiAdapter(
            (self.context, self.request),
            name='plone_portal_state')
        self.anonymous = portal_state.anonymous()
        if not self.anonymous:
            member = portal_state.member()
            user_id = member.getId()
            if user_id != 'admin':
                return user_id
        return None

    # def getCommunityTab(self):
    #     portal = self.portal()
    #     url = portal.absolute_url()
    #     path_url = portal.absolute_url_path()
    #     path = path_url + self.context.replace(url, '')
    #     community = api.content.find(path=path, depth=0)[0].getObject()
    #     import ipdb; ipdb.set_trace()
    #     if community.tab_view == 'Documents':
    #         # string:${object_url/@@ulearn.utils/getCommunityTab}
    #         #self.request.response.redirect(self.context + '/documents')
    #         return self.context + '/documents'
    #     return self.context

# def isInstalledProduct(self, package):
#     qi = api.portal.get_tool(name='portal_quickinstaller')
#     prods = qi.listInstalledProducts()
#     for prod in prods:
#         if prod['id'] == package:
#             return True
#     return False


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


# Función que convierte cualquier objeto JSON decodificado de usar cadenas Unicode
# a cadenas de bytes codificadas en UTF-8
def byteify(input):
    if isinstance(input, dict):
        return {byteify(key): byteify(value)
                for key, value in input.iteritems()}
    elif isinstance(input, list):
        return [byteify(element) for element in input]
    elif isinstance(input, unicode):
        return input.encode('utf-8')
    else:
        return input


@ram.cache(lambda *args: time() // (60 * 60))
def isBirthdayInProfile():
    user_properties_utility = getUtility(ICatalogFactory, name='user_properties')
    attributes = user_properties_utility.properties + METADATA_USER_ATTRS

    try:
        extender_name = api.portal.get_registry_record(
            'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
    except:
        extender_name = ''

    if extender_name:
        if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
            extended_user_properties_utility = getUtility(
                ICatalogFactory, name=extender_name)
            attributes.extend([element
                               for element in extended_user_properties_utility.properties
                               if element not in attributes])

    return 'birthday' in attributes


def getCommunityNameFromObj(self, value):
    portal_state = self.context.unrestrictedTraverse('@@plone_portal_state')
    root = getNavigationRootObject(self.context, portal_state.portal())
    physical_path = value.getPhysicalPath()
    relative = physical_path[len(root.getPhysicalPath()):]
    for i in range(len(relative)):
        now = relative[:i + 1]
        obj = aq_inner(root.unrestrictedTraverse(now))
        if (ICommunity.providedBy(obj)):
            return obj.title
    return ''


def replaceImagePathByURL(msg):
    srcs = re.findall('src="([^"]+)"', msg)

    # Transformamos imagenes internas
    uids = re.findall(r"resolveuid/(.*?)/@@images", msg)
    for i in range(len(uids)):
        thumb_url = api.content.get(UID=uids[i]).absolute_url() + '/thumbnail-image'
        plone_url = srcs[i]
        msg = re.sub(plone_url, thumb_url, msg)

    # Transformamos imagenes contra la propia web
    images = re.findall(r"/@@images/.*?\"", msg)
    for i in range(len(images)):
        msg = re.sub(images[i], '/thumbnail-image"', msg)

    return msg


def calculatePortalTypeOfInternalPath(url, portal_url):
    site = api.portal.get()
    base_path = '/'.join(site.getPhysicalPath())
    partial_path = url.split(portal_url)[1]
    partial_path.replace('#', '')  # Sanitize if necessary
    if partial_path.endswith('/view/'):
        partial_path = partial_path.split('/view/')[0]
    elif partial_path.endswith('/view'):
        partial_path = partial_path.split('/view')[0]
    custom_path = base_path + partial_path.encode('utf-8')
    try:
        if 'resolveuid' in custom_path:
            nextObj = api.content.get(UID=custom_path.split('resolveuid/')[-1])
        else:
            nextObj = api.content.get(path=custom_path)
        return nextObj.Type()
    except:
        return None


# HTML Parser
ATTRS_TO_REMOVE = [
    'lang', 'language', 'onmouseover', 'onmouseout', 'script', 'style', 'font',
    'dir', 'face', 'size', 'color', 'style', 'class', 'width', 'height', 'hspace',
    'border', 'valign', 'align', 'background', 'bgcolor', 'text', 'link', 'vlink',
    'alink', 'cellpadding', 'cellspacing']

TAGS_TO_REMOVE = [
    "article", "aside", "audio", "bdo", "big", "canvas", "col", "colgroup",
    "command", "datalist", "dd", "del", "details", "dfn", "dialog", "dl",
    "dt", "footer", "head", "header", "hgroup", "ins", "kbd", "keygen",
    "map", "mark", "meter", "nav", "output", "progress", "rp", "rt",
    "ruby", "samp", "section", "sub", "sup", "var",
    "video", "script"]

# These are empty elements, but they are relevant for the visualization of the html
TAGS_TO_KEEP = ["br", "iframe", "img", "input"]


def HTMLParser(html):
    soup = BeautifulSoup(html, "html.parser")

    """ Remove specific tags """
    for tag_name in TAGS_TO_REMOVE:
        tags = soup.find_all(tag_name)
        for TAG in tags:
            TAG.decompose()

    """ Remove useless attrs """
    for tag in soup.find_all():
        for attr in list(tag.attrs):
            if attr in ATTRS_TO_REMOVE:
                del tag[attr]

    """ Remove empty tags. Separated from the other loop for readability """
    for tag in soup.find_all():
        remove_empty_tags(tag)

    return soup.prettify()


def remove_empty_tags(el):
    if el.can_be_empty_element:
        return

    if (not el.contents or is_whitespace_content(el.contents)) and el.name not in TAGS_TO_KEEP:
        if el.parent:
            parent = el.parent
            el.decompose()
            remove_empty_tags(parent)
            return

        el.decompose()
        return

    for child in el.children:
        if isinstance(child, Tag):
            remove_empty_tags(child)


def is_whitespace_content(content):
    return all(isinstance(item, NavigableString) and not item.strip() for item in content)
