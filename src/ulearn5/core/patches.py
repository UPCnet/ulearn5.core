# -*- encoding: utf-8 -*-
import copy

from plone import api
from zope.component import getUtility
from zope.component import getUtilitiesFor
from zope.interface import implements
from souper.interfaces import ICatalogFactory

from Acquisition import aq_inner
from zExceptions import Forbidden
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import ILanguageSchema
from mrs5.max.utilities import IMAXClient
from plone.i18n.interfaces import INegotiateLanguage
from plone.registry.interfaces import IRegistry
from repoze.catalog.query import Eq
from souper.soup import get_soup

from base5.core.utils import remove_user_from_catalog
from ulearn5.core.gwuuid import IGWUUID

import logging
logger = logging.getLogger('event.LDAPMultiPlugin')


# We are patching the enumerateUsers method of the mutable_properties plugin to
# make it return all the available user properties extension
def enumerateUsers(self, id=None, login=None, exact_match=False, **kw):
        """ See IUserEnumerationPlugin.
        """
        plugin_id = self.getId()
        # This plugin can't search for a user by id or login, because there is
        # no such keys in the storage (data dict in the comprehensive list)
        # If kw is empty or not, we continue the search.
        if id is not None or login is not None:
            return ()

        criteria = copy.copy(kw)

        users = [(user, data) for (user, data) in self._storage.items()
                 if self.testMemberData(data, criteria, exact_match)
                 and not data.get('isGroup', False)]

        has_extended_properties = False
        extender_name = api.portal.get_registry_record('base5.core.controlpanel.core.IGenwebCoreControlPanelSettings.user_properties_extender')

        if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
            has_extended_properties = True
            extended_user_properties_utility = getUtility(ICatalogFactory, name=extender_name)

        user_properties_utility = getUtility(ICatalogFactory, name='user_properties')

        users_profile = []
        for user_id, user in users:
            if user is not None:
                user_dict = {}
                for user_property in user_properties_utility.properties:
                    user_dict.update({user_property: user.get(user_property, '')})

                if has_extended_properties:
                    for user_property in extended_user_properties_utility.properties:
                        user_dict.update({user_property: user.get(user_property, '')})

                user_dict.update(dict(id=user_id))
                user_dict.update(dict(login=user_id))
                user_dict.update(dict(title=user.get('fullname', user_id)))
                user_dict.update(dict(description=user.get('fullname', user_id)))
                user_dict.update({'pluginid': plugin_id})
                users_profile.append(user_dict)

        return tuple(users_profile)


def deleteMembers(self, member_ids):
    # this method exists to bypass the 'Manage Users' permission check
    # in the CMF member tool's version
    context = aq_inner(self.context)
    mtool = getToolByName(self.context, 'portal_membership')
    # Delete members in acl_users.
    acl_users = context.acl_users
    if isinstance(member_ids, basestring):
        member_ids = (member_ids,)
    member_ids = list(member_ids)
    for member_id in member_ids[:]:
        member = mtool.getMemberById(member_id)
        if member is None:
            member_ids.remove(member_id)
        else:
            if not member.canDelete():
                raise Forbidden
            if 'Manager' in member.getRoles() and not self.is_zope_manager:
                raise Forbidden
    try:
        acl_users.userFolderDelUsers(member_ids)
    except (AttributeError, NotImplementedError):
        raise NotImplementedError('The underlying User Folder '
                                  'doesn\'t support deleting members.')

    self.maxclient, self.settings = getUtility(IMAXClient)()
    self.maxclient.setActor(self.settings.max_restricted_username)
    self.maxclient.setToken(self.settings.max_restricted_token)

    for member_id in member_ids:
        remove_user_from_catalog(member_id.lower())
        pc = api.portal.get_tool(name='portal_catalog')

        communities_subscription = self.maxclient.people[member_id].subscriptions.get()

        if communities_subscription != []:

            for num, community_subscription in enumerate(communities_subscription):
                community = pc.unrestrictedSearchResults(portal_type="ulearn.community", community_hash=community_subscription['hash'])
                try:
                    obj = community[0]._unrestrictedGetObject()
                    self.context.plone_log('Processant {} de {}. Comunitat {}'.format(num, len(communities_subscription), obj))
                    gwuuid = IGWUUID(obj).get()
                    portal = api.portal.get()
                    soup = get_soup('communities_acl', portal)

                    records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

                    # Save ACL into the communities_acl soup
                    if records:
                        acl_record = records[0]
                        acl = acl_record.attrs['acl']
                        exist = [a for a in acl['users'] if a['id'] == unicode(member_id)]
                        if exist:
                            acl['users'].remove(exist[0])
                            acl_record.attrs['acl'] = acl
                            soup.reindex(records=[acl_record])
                            adapter = obj.adapted()
                            adapter.set_plone_permissions(adapter.get_acl())

                except:
                    continue

    # Delete member data in portal_memberdata.
    mdtool = getToolByName(context, 'portal_memberdata', None)
    if mdtool is not None:
        for member_id in member_ids:
            mdtool.deleteMemberData(member_id)
            try:
                self.maxclient.people[member_id].delete()
            except:
                # No existe el usuari en max
                pass

    # Delete members' local roles.
    mtool.deleteLocalRoles(getUtility(ISiteRoot), member_ids,
                           reindex=1, recursive=1)


class NegotiateLanguage(object):
    """Perform default language negotiation"""
    implements(INegotiateLanguage)

    def __init__(self, site, request):
        """Setup the current language stuff."""
        registry = getUtility(IRegistry)
        lan_tool = registry.forInterface(ILanguageSchema, prefix='plone')
        tool = api.portal.get_tool('portal_languages')
        langs = []
        useContent = lan_tool.use_content_negotiation
        useCcTLD = lan_tool.use_cctld_negotiation
        useSubdomain = lan_tool.use_subdomain_negotiation
        usePath = lan_tool.use_path_negotiation
        useCookie = lan_tool.use_cookie_negotiation
        setCookieEverywhere = lan_tool.set_cookie_always
        authOnly = lan_tool.authenticated_users_only
        useRequest = lan_tool.use_request_negotiation
        useDefault = 1  # This should never be disabled
        langsCookie = None

        if usePath:
            # This one is set if there is an allowed language in the current path
            langs.append(tool.getPathLanguage())

        if useContent:
            langs.append(tool.getContentLanguage())

        if useCookie and not (authOnly and tool.isAnonymousUser()):
            # If we are using the cookie stuff we provide the setter here
            set_language = tool.REQUEST.get('set_language', None)
            if set_language:
                langsCookie = tool.setLanguageCookie(set_language)
            else:
                # Get from cookie
                langsCookie = tool.getLanguageCookie()
            langs.append(langsCookie)

        if useSubdomain:
            langs.extend(tool.getSubdomainLanguages())

        if useCcTLD:
            langs.extend(tool.getCcTLDLanguages())

        # Get langs from request
        if useRequest:
            langs.extend(tool.getRequestLanguages())

        # Get default
        if useDefault:
            langs.append(tool.getDefaultLanguage())

        # Filter None languages
        langs = [lang for lang in langs if lang is not None]

        # Set cookie language to language
        if setCookieEverywhere and useCookie and langs[0] != langsCookie:
            tool.setLanguageCookie(langs[0], noredir=True)

        self.default_language = langs[-1]
        self.language = langs[0]
        self.language_list = langs[1:-1]

        # Patched to meet the feature requirements for the client
        custom_lang_cookie = request.cookies.get('I18N_LANGUAGE')
        if custom_lang_cookie:
            self.language = custom_lang_cookie


def authenticateCredentials(self, credentials):
    """ Fulfill AuthenticationPlugin requirements """
    acl = self._getLDAPUserFolder()
    login = credentials.get('login')
    password = credentials.get('password')

    if not acl or not login or not password:
        return None, None

    user = acl.getUser(login, pwd=password)

    if user is None:
        return None

    logger.error('XXX Successful login of {}'.format(login))
    return (user.getId(), user.getUserName())



from zope.event import notify
from plone.app.workflow.events import LocalrolesModifiedEvent
from Products.statusmessages.interfaces import IStatusMessage
from plone.app.workflow import PloneMessageFactory as _

# Notify LocalrolesModifiedEvent if settings
# plone.app.workflow.browser.sharing.SharingView
def handle_form(self):
        """
        We split this out so we can reuse this for ajax.
        Will return a boolean if it was a post or not
        """
        postback = True

        form = self.request.form
        submitted = form.get('form.submitted', False)
        save_button = form.get('form.button.Save', None) is not None
        cancel_button = form.get('form.button.Cancel', None) is not None

        if submitted and save_button and not cancel_button:
            if not self.request.get('REQUEST_METHOD', 'GET') == 'POST':
                raise Forbidden

            authenticator = self.context.restrictedTraverse('@@authenticator',
                                                            None)
            if not authenticator.verify():
                raise Forbidden

            # Update the acquire-roles setting
            if self.can_edit_inherit():
                inherit = bool(form.get('inherit', False))
                reindex = self.update_inherit(inherit, reindex=False)
            else:
                reindex = False

            # Update settings for users and groups
            entries = form.get('entries', [])
            roles = [r['id'] for r in self.roles()]
            settings = []
            for entry in entries:
                settings.append(
                    dict(id=entry['id'],
                         type=entry['type'],
                         roles=[r for r in roles
                            if entry.get('role_%s' % r, False)]))
            if settings:
                reindex = self.update_role_settings(settings, reindex=False) \
                            or reindex
                notify(LocalrolesModifiedEvent(self.context, self.request))
            if reindex:
                self.context.reindexObjectSecurity()
                notify(LocalrolesModifiedEvent(self.context, self.request))
            IStatusMessage(self.request).addStatusMessage(
                _(u"Changes saved."), type='info')

        # Other buttons return to the sharing page
        if cancel_button:
            postback = False

        return postback
