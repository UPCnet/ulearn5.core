# -*- coding: utf-8 -*-
from five import grok
from Acquisition import aq_chain
from zope.component import getUtility

from zope.component.hooks import getSite
from zope.container.interfaces import IObjectAddedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes

from ulearn5.core.interfaces import IAppImage
from ulearn5.core.interfaces import IAppFile
from ulearn5.core.content.community import ICommunity

from mrs5.max.utilities import IMAXClient
from plone import api
from souper.soup import get_soup
from souper.soup import Record
from repoze.catalog.query import Eq
from DateTime.DateTime import DateTime
from zope.component import providedBy
from plone.app.workflow.interfaces import ILocalrolesModifiedEvent
from Products.CMFPlone.interfaces import IConfigurationChangedEvent
from Products.PluggableAuthService.interfaces.events import IUserLoggedInEvent
from plone.event.interfaces import IRecurrenceSupport
from plone.app.contenttypes.interfaces import IFolder
from plone.app.contenttypes.interfaces import IEvent
from plone.app.contenttypes.interfaces import INewsItem
from zope.globalrequest import getRequest
from plone.namedfile.file import NamedBlobImage
from io import BytesIO as StringIO

from mrs5.max.browser.controlpanel import IMAXUISettings
from plone.registry.interfaces import IRegistry
from zope.component import queryUtility
from plone.dexterity.interfaces import IDexterityContent

from plone.memoize import ram
from time import time
# from ulearn5.core.formatting import formatMessageEntities
# from plone.app.textfield.value import RichTextValue

import io
import logging
import os
import PIL
import pytz
import requests
import transaction

logger = logging.getLogger(__name__)

articles = {
    'ca': dict(Document=u'un', File=u'un', Image=u'una', Link=u'un', Event=u'un', NewsItem=u'una', ExternalContent=u'un'),
    'es': dict(Document=u'un', File=u'un', Image=u'una', Link=u'un', Event=u'un', NewsItem=u'una', ExternalContent=u'un'),
    'en': dict(Document=u'a', File=u'a', Image=u'an', Link=u'a', Event=u'an', NewsItem=u'a', ExternalContent=u'a'),
}

tipus = {
    'ca': dict(Document=u'document', File=u'document', Image=u'foto', Link=u'enllaç', Event=u'esdeveniment', NewsItem=u'notícia', ExternalContent=u'arxiu protegit'),
    'es': dict(Document=u'documento', File=u'documento', Image=u'foto', Link=u'enlace', Event=u'evento', NewsItem=u'noticia', ExternalContent=u'archivo protegido'),
    'en': dict(Document=u'document', File=u'document', Image=u'photo', Link=u'link', Event=u'event', NewsItem=u'news item', ExternalContent=u'protected file'),
}

varnish_to_ban = os.environ.get('varnish_to_ban', '')


@grok.subscribe(IDexterityContent, IObjectAddedEvent)
def objectAdded(content, event):
    """ DextirityContent modified """
    portal = getSite()
    pm = getToolByName(portal, 'portal_membership')
    if pm.isAnonymousUser():  # the user has not logged in
        username = ''
        return
    else:
        member = pm.getAuthenticatedMember()

    registry = queryUtility(IRegistry)
    settings = registry.forInterface(IMAXUISettings, check=False)
    domain = settings.domain

    username = member.getUserName()
    memberdata = pm.getMemberById(username)
    content_path = "/".join(content.getPhysicalPath())
    physical_path = content.getPhysicalPath()
    relative = physical_path[len(portal.getPhysicalPath()):]

    if portal.unrestrictedTraverse(relative[0]).Type() == u'Comunitat':
        logger.error('XXX DexterityContent Object added:' + content_path + ';comunitat:' + relative[0] + ';username:' + username + ';domain:' + domain)
    else:
        try:
            logger.error('XXX DexterityContent Object added:' + content_path + ';comunitat:__NO_COMMUNITY;username:' + username + ';domain:' + domain)
        except:
            logger.error('XXX DexterityContent Object added:' + content_path + ';comunitat:__NO_COMMUNITY;username:' + username + ';domain:nodomain')


@grok.subscribe(IDexterityContent, IObjectModifiedEvent)
def objectModified(content, event):
    """ DextirityContent modified """
    portal = getSite()
    pm = getToolByName(portal, 'portal_membership')
    if pm.isAnonymousUser():  # the user has not logged in
        username = ''
        return
    else:
        member = pm.getAuthenticatedMember()

    registry = queryUtility(IRegistry)
    settings = registry.forInterface(IMAXUISettings, check=False)
    domain = settings.domain

    username = member.getUserName()
    memberdata = pm.getMemberById(username)
    content_path = "/".join(content.getPhysicalPath())
    physical_path = content.getPhysicalPath()
    relative = physical_path[len(portal.getPhysicalPath()):]
    if username == None:
        username = ''
    if portal.unrestrictedTraverse(relative[0]).Type() == u'Comunitat':
        logger.error('XXX DexterityContent Object modified:' + content_path + ';comunitat:' + relative[0] + ';username:' + username + ';domain:' + domain)
    else:
        try:
            logger.error('XXX DexterityContent Object modified:' + content_path + ';comunitat:__NO_COMMUNITY;username:' + username + ';domain:' + domain)
        except:
            logger.error('XXX DexterityContent Object modified:' + content_path + ';comunitat:__NO_COMMUNITY;username:' + username + ';domain:nodomain')

    if varnish_to_ban != '':
        requests.request('BAN', varnish_to_ban, headers={'X-Ban': '.*/'.join(content.getPhysicalPath()[1:3]) + '.*'}, timeout=1)


@grok.subscribe(ICommunity, IObjectAddedEvent)
def communityAdded(content, event):
    """ Community added handler
    """
    portal = getSite()
    pm = getToolByName(portal, 'portal_membership')
    pl = getToolByName(portal, 'portal_languages')
    default_lang = pl.getDefaultLanguage()

    if pm.isAnonymousUser():  # the user has not logged in
        username = ''
        return
    else:
        member = pm.getAuthenticatedMember()

    username = member.getUserName()
    memberdata = pm.getMemberById(username)
    oauth_token = memberdata.getProperty('oauth_token', None)

    maxclient, settings = getUtility(IMAXClient)()
    maxclient.setActor(username)
    maxclient.setToken(oauth_token)

    activity_text = {
        'ca': u'He creat una nova comunitat: {}',
        'es': u'He creado una comunidad nueva: {}',
        'en': u'I\'ve just created a new community: {}',
    }

    try:
        maxclient.people[username].activities.post(object_content=activity_text[default_lang].format(content.Title().decode('utf-8')), contexts=[dict(url=content.absolute_url(), objectType="context")])
    except:
        logger.warning('The username {} has been unable to post the default community creation message'.format(username))


def Added(content, event):
    """ MAX hooks main handler
    """
    portal = getSite()
    pm = getToolByName(portal, 'portal_membership')
    pl = getToolByName(portal, 'portal_languages')
    default_lang = pl.getDefaultLanguage()

    community = findContainerCommunity(content)

    if not community or \
       IAppFile.providedBy(content) or \
       IAppImage.providedBy(content):
        # For some reason the file we are creating is not inside a community
        # or the content is created externaly through apps via the upload ws
        return

    if content.portal_type == 'News Item':
        if event.transition is None:
            return
        elif event.transition.id != 'publicaalaintranet':
            return

    if content.portal_type == 'ExternalContent':
        if event.transition is None:
            return
        elif event.transition.id != 'publishtointranet':
            return

    username, oauth_token = getUserOauthToken(pm)
    maxclient = connectMaxclient(username, oauth_token)

    parts = dict(type=tipus[default_lang].get(content.portal_type.replace(" ", ""), ''),
                 name=content.Title().decode('utf-8') or getattr(getattr(content, 'file', u''), 'filename', u'').decode('utf-8') or getattr(getattr(content, 'image', u''), 'filename', u'').decode('utf-8'),
                 link='{}/view'.format(content.absolute_url()),
                 un=articles[default_lang].get(content.portal_type.replace(" ", ""), 'un'))

    activity_text = {
        'ca': u'He afegit {un} {type} "{name}" a {link}',
        'es': u'He añadido {un} {type} "{name}" a {link}',
        'en': u'I\'ve added {un} {type} "{name}" a {link}',
    }

    addPost = addActivityPost(content)

    if addPost:
        if (content.portal_type == 'Image' or
           content.portal_type == 'File') and \
           content.description:
            activity_text = u'{} {}'.format(content.title, u'{}/view'.format(content.absolute_url()))

            try:
                maxclient.people[username].activities.post(object_content=activity_text, contexts=[dict(url=community.absolute_url(), objectType='context')])
            except:
                logger.warning('The username {} has been unable to post the default object creation message'.format(username))
        else:
            try:
                maxclient.people[username].activities.post(object_content=activity_text[default_lang].format(**parts), contexts=[dict(url=community.absolute_url(), objectType='context')])
            except:
                logger.warning('The username {} has been unable to post the default object creation message'.format(username))


def Modified(content, event):
    """ Max hooks modified handler """
    # Avoid execution when trigered on sharing changes
    is_sharing_event = providedBy(event)(ILocalrolesModifiedEvent)
    if is_sharing_event:
        return

    portal = getSite()
    pm = getToolByName(portal, 'portal_membership')
    pl = getToolByName(portal, 'portal_languages')
    default_lang = pl.getDefaultLanguage()

    community = findContainerCommunity(content)

    if not community or \
       IAppFile.providedBy(content) or \
       IAppImage.providedBy(content):
        # For some reason the file we are creating is not inside a community
        # or the content is created externaly through apps via the upload ws
        return

    username, oauth_token = getUserOauthToken(pm)
    maxclient = connectMaxclient(username, oauth_token)

    parts = dict(type=tipus[default_lang].get(content.portal_type, ''),
                 name=content.Title().decode('utf-8') or getattr(getattr(content, 'file', u''), 'filename', u'').decode('utf-8') or getattr(getattr(content, 'image', u''), 'filename', u'').decode('utf-8'),
                 link='{}/view'.format(content.absolute_url()),
                 un=articles[default_lang].get(content.portal_type, 'un'))

    activity_text = {
        'ca': u'He modificat {un} {type} "{name}" a {link}',
        'es': u'He modificado {un} {type} "{name}" a {link}',
        'en': u'I\'ve modified {un} {type} "{name}" a {link}',
    }

    addPost = addActivityPost(content)

    if addPost:
        if (content.portal_type == 'Image' or
           content.portal_type == 'File') and \
           content.description:
            activity_text = u'{} {}'.format(content.title, u'{}/view'.format(content.absolute_url()))

            try:
                maxclient.people[username].activities.post(object_content=activity_text, contexts=[dict(url=community.absolute_url(), objectType='context')])
            except:
                logger.warning('The username {} has been unable to post the default object creation message'.format(username))
        else:
            try:
                maxclient.people[username].activities.post(object_content=activity_text[default_lang].format(**parts), contexts=[dict(url=community.absolute_url(), objectType='context')])
            except:
                logger.warning('The username {} has been unable to post the default object creation message'.format(username))


def findContainerCommunity(content):
    for parent in aq_chain(content):
        if ICommunity.providedBy(parent):
            return parent

    return None


@ram.cache(lambda *args: time() // (60 * 60))
def packages_installed():
    portal = getSite()

    qi_tool = getToolByName(portal, 'portal_quickinstaller')
    installed = [p['id'] for p in qi_tool.listInstalledProducts()]
    return installed


def addActivityPost(content):
    installed = packages_installed()
    if 'ulearn5.abacus' in installed:
        if content.portal_type == 'Event':
            return False

    for parent in aq_chain(content):
        if parent.portal_type == 'privateFolder':
            return False
        elif ICommunity.providedBy(parent):
            return True

    return None


def getUserOauthToken(pm):
    if pm.isAnonymousUser():  # the user has not logged in
        username = ''
        return
    else:
        member = pm.getAuthenticatedMember()

    username = member.getUserName().lower()
    memberdata = pm.getMemberById(username)
    oauth_token = memberdata.getProperty('oauth_token', None)

    return username, oauth_token


def connectMaxclient(username, oauth_token):
    maxclient, settings = getUtility(IMAXClient)()
    maxclient.setActor(username)
    maxclient.setToken(oauth_token)

    return maxclient


@grok.subscribe(ICommunity, IObjectAddedEvent)
def UpdateUserCommunityAccess(content, event):
    """ Update data access to the user community when you add content to the community
    """
    portal = getSite()
    community = findContainerCommunity(content)
    current_user = api.user.get_current()
    user_community = current_user.id + '_' + community.id
    soup_access = get_soup('user_community_access', portal)
    exist = [r for r in soup_access.query(Eq('user_community', user_community))]
    if not exist:
        record = Record()
        record.attrs['user_community'] = user_community
        record.attrs['data_access'] = DateTime()
        soup_access.add(record)
    else:
        exist[0].attrs['data_access'] = DateTime()
    soup_access.reindex()


@grok.subscribe(IConfigurationChangedEvent)
def updateCustomLangCookie(event):
    """ This subscriber will trigger when a user change his/her profile data. It
        sets a cookie for the 'language' user profile setting. After this, due
        to the custom Language Negotiator set for the Blanquerna layer, the site
        language is forced to the one in the cookie.
    """
    if 'language' in event.data:
        if event.data['language']:
            event.context.request.response.setCookie('I18N_LANGUAGE', event.data['language'], path='/')
            event.context.request.response.redirect(event.context.context.absolute_url() + '/@@personal-information')


@grok.subscribe(IUserLoggedInEvent)
def updateCustomLangCookieLogginIn(event):
    """ This subscriber will trigger when a user change his/her profile data. It
        sets a cookie for the 'language' user profile setting. After this, due
        to the custom Language Negotiator set for the Blanquerna layer, the site
        language is forced to the one in the cookie.
    """
    request = getRequest()
    current = api.user.get_current()
    lang = current.getProperty('language')
    if lang and request is not None:
        request.response.setCookie('I18N_LANGUAGE', lang, path='/')


@grok.subscribe(INewsItem, IObjectAddedEvent)
@grok.subscribe(INewsItem, IObjectModifiedEvent)
def CreateThumbImage(content, event):
    """ Update thumb from News Item image on save
    """
    if getattr(content, 'image', None):
        content_type = content.image.contentType
        filename = content.image.filename
        raw_file = content.image.data
        raw_content = StringIO(raw_file)
        img = PIL.Image.open(raw_content).convert('RGB')

        basewidth = 450
        wpercent = basewidth / float(img.size[0])
        hsize = int(float(img.size[1]) * float(wpercent))
        resized = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
        output_tmp = io.BytesIO()
        resized.save(output_tmp, format='JPEG')
        hex_data = output_tmp.getvalue()
        thumb_image = NamedBlobImage(
            data=hex_data,
            filename=filename,
            contentType=str(content_type))
        content.thumbnail_image = thumb_image
    else:
        content.thumbnail_image = None


@grok.subscribe(ICommunity, IObjectAddedEvent)
@grok.subscribe(ICommunity, IObjectModifiedEvent)
def CreateThumbImageCommunity(content, event):
    """ Update thumb from Community image on save
    """
    if getattr(content, 'image', None):
        content_type = content.image.contentType
        filename = content.image.filename
        raw_file = content.image.data
        raw_content = StringIO(raw_file)
        img = PIL.Image.open(raw_content).convert('RGB')

        basewidth = 150
        wpercent = basewidth / float(img.size[0])
        hsize = int(float(img.size[1]) * float(wpercent))
        resized = img.resize((basewidth, hsize), PIL.Image.ANTIALIAS)
        output_tmp = io.BytesIO()
        resized.save(output_tmp, format='JPEG')
        hex_data = output_tmp.getvalue()
        thumb_image = NamedBlobImage(
            data=hex_data,
            filename=filename,
            contentType=str(content_type))
        content.thumbnail_image = thumb_image
    else:
        content.thumbnail_image = None

# Esto incluye el bitly en el contenido de las noticias
# el problema es que cuando vas a modificar la url externa aparece el bitly
# y pierdes lo que habias puesto
# @grok.subscribe(INewsItem, IObjectAddedEvent)
# @grok.subscribe(INewsItem, IObjectModifiedEvent)
# def CreateBitlyURL(content, event):
#     """ Create bitlyurl in text News Item
#     """
#     if getattr(content, 'text', None):
#         text = formatMessageEntities(content.text.output)
#         content.text = RichTextValue(text)
#     else:
#         content.text = None


@grok.subscribe(IFolder, IObjectAddedEvent)
def setLocallyAllowedTypesFolder(content, event):
    menuPath = '/'.join(api.portal.get().getPhysicalPath()) + '/gestion/menu/'
    en = menuPath + 'en'
    ca = menuPath + 'ca'
    es = menuPath + 'es'
    languagePath = [ca, es, en]

    parentPath = '/'.join(content.aq_parent.getPhysicalPath())
    if parentPath in languagePath:
        behavior = ISelectableConstrainTypes(content)
        behavior.setLocallyAllowedTypes(('Link',))
        behavior.setImmediatelyAddableTypes(('Link',))
        transaction.commit()

@grok.subscribe(IEvent, IObjectAddedEvent)
@grok.subscribe(IEvent, IObjectModifiedEvent)
def setEventTimezone(content, event):
    if content.timezone:
        if content.start.tzinfo.zone != content.timezone:
            adapter = IRecurrenceSupport(content, None)
            if adapter:
                for con in adapter.occurrences():
                    sintzinfo_start = con.start.replace(tzinfo=None)
                    con.start = pytz.timezone(content.timezone).localize(sintzinfo_start)
                    sintzinfo_end = con.end.replace(tzinfo=None)
                    con.end = pytz.timezone(content.timezone).localize(sintzinfo_end)
                    con.reindexObject()
            transaction.commit()
    else:
        current_user = api.user.get_current()
        content.timezone = current_user.getProperty('timezone')