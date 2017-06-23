# -*- coding: utf-8 -*-
from five import grok
from Acquisition import aq_chain
from zope.component import getUtility

from zope.component.hooks import getSite
from zope.container.interfaces import IObjectAddedEvent

from Products.CMFCore.utils import getToolByName

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
from plone.app.controlpanel.interfaces import IConfigurationChangedEvent
from Products.PluggableAuthService.interfaces.events import IUserLoggedInEvent
from zope.globalrequest import getRequest

import logging

logger = logging.getLogger(__name__)

articles = {
    'ca': dict(File=u'un', Image=u'una', Link=u'un', Event=u'un'),
    'es': dict(File=u'un', Image=u'una', Link=u'un', Event=u'un'),
    'en': dict(File=u'a', Image=u'an', Link=u'a', Event=u'an'),
}

tipus = {
    'ca': dict(Document=u'document', File=u'document', Image=u'foto', Link=u'enllaç', Event=u'esdeveniment'),
    'es': dict(Document=u'documento', File=u'documento', Image=u'foto', Link=u'enlace', Event=u'evento'),
    'en': dict(Document=u'document', File=u'document', Image=u'photo', Link=u'link', Event=u'event'),
}


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

    username, oauth_token = getUserOauthToken(pm)
    maxclient = connectMaxclient(username, oauth_token)

    parts = dict(type=tipus[default_lang].get(content.portal_type, ''),
                 name=content.Title().decode('utf-8') or getattr(getattr(content, 'file', u''), 'filename', u'').decode('utf-8') or getattr(getattr(content, 'image', u''), 'filename', u'').decode('utf-8'),
                 link='{}/view'.format(content.absolute_url()),
                 un=articles[default_lang].get(content.portal_type, 'un'))

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


def addActivityPost(content):
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
            event.context.request.response.setCookie('uLearn_I18N_Custom', event.data['language'], path='/')
            event.context.request.response.redirect(event.context.context.absolute_url()+'/@@personal-information')


@grok.subscribe(IUserLoggedInEvent)
def updateCustomLangCookieLogginIn(event):
    """ This subscriber will trigger when a user change his/her profile data. It
       sets a cookie for the 'language' user profile setting. After this, due
        to the custom Language Negotiator set for the Blanquerna layer, the site
        language is forced to the one in the cookie.
    """
    request = getRequest()
    lang = event.object.getProperty('language', None)
    if lang and request is not None:
        request.response.setCookie('uLearn_I18N_Custom', lang, path='/')
