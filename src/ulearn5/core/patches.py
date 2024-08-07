# -*- encoding: utf-8 -*-
import copy
import z3c.form.interfaces

from plone import api
from zope.component import getMultiAdapter
from zope.component import getSiteManager
from zope.component import getUtility
from zope.component import getUtilitiesFor
from zope.interface import implements
from zope.interface import providedBy
from souper.interfaces import ICatalogFactory

from AccessControl import ClassSecurityInfo
from AccessControl import Unauthorized
from Acquisition import aq_inner
from zExceptions import Forbidden
from Products.CMFCore.interfaces import ISiteRoot
from Products.CMFCore.permissions import View
from Products.CMFPlone import utils
from Products.CMFPlone.interfaces import ILanguageSchema
from mrs5.max.utilities import IMAXClient
from plone.app.users.browser.personalpreferences import PersonalPreferencesPanel
from plone.i18n.interfaces import INegotiateLanguage
from plone.registry.interfaces import IRegistry
from repoze.catalog.query import Eq
from souper.soup import get_soup
from souper.soup import Record

from base5.core.patches import deletePersonalPortrait
from base5.core.utils import remove_user_from_catalog
from ulearn5.core.gwuuid import IGWUUID

import logging
logger = logging.getLogger('event.LDAPMultiPlugin')


# We are patching the enumerateUsers method of the mutable_properties plugin to
# make it return all the available user properties extension
def enumerateUsers(self, id=None, login=None, exact_match=False, **kw):
        """ See IUserEnumerationPlugin.
        """

        installed = packages_installed()
        if 'base5.core' in installed:
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
            extender_name = api.portal.get_registry_record('base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')

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
        else:
            return None


def deleteMembers(self, member_ids):
    # this method exists to bypass the 'Manage Users' permission check
    # in the CMF member tool's version
    context = aq_inner(self.context)
    mtool = api.portal.get_tool(name='portal_membership')

    # Delete members in acl_users.
    acl_users = context.acl_users
    if isinstance(member_ids, basestring):
        member_ids = (member_ids,)
    member_ids = list(member_ids)
    for member_id in member_ids[:]:
        mtool.deletePersonalPortrait(str(member_id))
        logger.info('Eliminat avatar usuari {}'.format(member_id))

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
        logger.info('Eliminat usuari {} del catalog.'.format(member_id.lower()))
        pc = api.portal.get_tool(name='portal_catalog')

        communities_subscription = self.maxclient.people[member_id].subscriptions.get()

        if communities_subscription != []:

            for num, community_subscription in enumerate(communities_subscription):
                community = pc.unrestrictedSearchResults(portal_type="ulearn.community", community_hash=community_subscription['hash'])
                try:
                    obj = community[0]._unrestrictedGetObject()
                    logger.info('Processant {} de {}. Comunitat {}'.format(num, len(communities_subscription), obj))
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
    mdtool = api.portal.get_tool(name='portal_memberdata')
    if mdtool is not None:
        for member_id in member_ids:
            mdtool.deleteMemberData(member_id)
            logger.info('Eliminat usuari {} del portal_memberdata.'.format(member_id))

            # Guardamos el username en el soup para borrar el usuario del local roles
            portal = api.portal.get()
            soup_users_delete = get_soup('users_delete_local_roles', portal)
            exist = [r for r in soup_users_delete.query(Eq('id_username', member_id))]

            if not exist:
                record = Record()
                record.attrs['id_username'] = member_id
                soup_users_delete.add(record)
                soup_users_delete.reindex()

            try:
                self.maxclient.people[member_id].delete()
            except:
                # No existe el usuari en max
                pass

    # OJO se quita porque si el site es muy grande al recorrer todo para borrar da Time-out y
    # ademas consume mucha memoria y tumba los zopes.
    # Hemos creado la vista delete_local_roles en base5.core.setup.py que ejecuta esto.

    # Delete members' local roles.
    #mtool.deleteLocalRoles(getUtility(ISiteRoot), member_ids,
    #                       reindex=1, recursive=1)
    #logger.info('Eliminat usuari {} del local roles.'.format(member_id))


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
            set_language = request.get('set_language', None)
            if set_language:
                langsCookie = tool.setLanguageCookie(
                    set_language,
                    request=request
                )
            else:
                # Get from cookie
                langsCookie = tool.getLanguageCookie(request)
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

        if useCookie:
            # Patched to meet the feature requirements for the client
            custom_lang_cookie = request.cookies.get('I18N_LANGUAGE')
            if custom_lang_cookie:
                self.language = custom_lang_cookie


from plone.registry.interfaces import IRegistry
from zope.component import queryUtility
from mrs5.max.browser.controlpanel import IMAXUISettings
from ulearn5.core.hooks import packages_installed

def authenticateCredentials(self, credentials):
    """ Fulfill AuthenticationPlugin requirements """
    acl = self._getLDAPUserFolder()
    login = credentials.get('login')
    password = credentials.get('password')

    if not acl or not login or not password:
        return None, None

    installed = packages_installed()
    if 'ulearn5.enginyersbcn' in installed:
         ldap_users = ['ulearn.user1', 'ulearn.user2', 'ulearn.user3', 'administrador1', 'administrador2', 'administrador3', 'comunicacio1', 'comunicacio2', 'dega', 'sac', 'sot', 'saj', 'formacio', 'sopp']
         if login not in ldap_users:
             return None

    user = acl.getUser(login, pwd=password)

    if user is None:
        return None

    registry = queryUtility(IRegistry)
    settings = registry.forInterface(IMAXUISettings, check=False)
    domain = settings.domain
    if domain == 'wecredit':
        logger.error('XXX Successful login of {}'.format(login))
    else:
        logger.error('XXX Successful login of {} in domain {}'.format(login, domain))

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
                         roles=[r for r in roles if entry.get('role_%s' % r, False)]))
            if settings:
                reindex = self.update_role_settings(settings, reindex=False) or reindex
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


from AccessControl import getSecurityManager
from plone.portlets.interfaces import IPortletManager
from plone.app.contentmenu.menu import PortletManagerSubMenuItem
from zope.component import getUtility
from plone.registry.interfaces import IRegistry
from zope.component import getUtilitiesFor
from plone.protect.utils import addTokenToUrl
from ulearn5.core import _
from zope.component.hooks import getSite


def getPortletMenuItems(self, context, request):
        """Return menu item entries in a TAL-friendly form."""
        items = []
        sm = getSecurityManager()
        # Bail out if the user can't manage portlets
        if not sm.checkPermission(
                PortletManagerSubMenuItem.MANAGE_SETTINGS_PERMISSION,
                context
        ):
            return items

        blacklist = getUtility(IRegistry).get(
            'plone.app.portlets.PortletManagerBlacklist', [])
        managers = getUtilitiesFor(IPortletManager)
        current_url = context.absolute_url()
        portal_url = getSite().absolute_url()

        items.append({
            'title': _(u'manage_homepage_portlets_title', default=u'Homepage'),
            'description': _(u'manage_homepage_portlets_description', default=u'Manage homepage portlets'),
            'action': addTokenToUrl(
                '{0}/front-page/@@manage-portletsbelowtitlecontent'.format(
                    portal_url),
                request),
            'selected': False,
            'icon': None,
            'extra': {
                'id': 'portlet-manager-all',
                'separator': None},
            'submenu': None,
        })

        for manager in managers:
            manager_name = manager[0]
            # Don't show items like 'plone.dashboard1' by default
            if manager_name in blacklist:
                continue

            item = {
                'title': _(manager_name,
                           default=u' '.join(manager_name.split('.')).title()),
                'description': manager_name,
                'action': addTokenToUrl(
                    '{0}/@@topbar-manage-portlets/{1}'.format(
                        current_url,
                        manager_name),
                    request),
                'selected': False,
                'icon': None,
                'extra': {
                    'id': 'portlet-manager-{0}'.format(manager_name),
                    'separator': None},
                'submenu': None,
            }

            if manager_name == 'plone.leftcolumn':
                item['title'] = _(u'manage_left_portlets_title', default=u'Left')
                item['description'] = _(u'manage_left_portlets_description', default=u'Manage left portlets')
            elif manager_name == 'plone.rightcolumn':
                item['title'] = _(u'manage_right_portlets_title', default=u'Right')
                item['description'] = _(u'manage_right_portlets_description', default=u'Manage right portlets')

            items.append(item)

        return items


def addable_portlets(self):
    baseUrl = self.baseUrl()
    addviewbase = baseUrl.replace(self.context_url(), '')

    def sort_key(v):
        return v.get('title')

    def check_permission(p):
        addview = p.addview
        if not addview:
            return False

        addview = "%s/+/%s" % (addviewbase, addview,)
        if addview.startswith('/'):
            addview = addview[1:]
        try:
            self.context.restrictedTraverse(str(addview))
        except (AttributeError, KeyError, Unauthorized,):
            return False
        return True

    current = api.user.get_current()
    lang = current.getProperty('language')
    portlets = [{
        'title': self.context.translate(p.title, domain='ulearn.portlets', target_language=lang),
        'description': p.description,
        'addview': '%s/+/%s' % (addviewbase, p.addview)
        } for p in self.manager.getAddablePortletTypes() if check_permission(p)]

    portlets.sort(key=sort_key)
    return portlets


security = ClassSecurityInfo()

@security.protected(View)
def getAvailableLayouts(self):
    # Get the layouts registered for this object from its FTI.
    fti = self.getTypeInfo()
    if fti is None:
        return ()
    result = []
    method_ids = fti.getAvailableViewMethods(self)
    current = api.user.get_current()
    lang = current.getProperty('language')
    for mid in method_ids:
        title = self.translate(mid, domain='ulearn.displays', target_language=lang)
        result.append((mid, title))
    return result


def updateWidgetsPersonalPreferences(self):
    super(PersonalPreferencesPanel, self).updateWidgets()

    self.widgets['language'].noValueMessage = _(
        u"vocabulary-missing-single-value-for-edit",
        u"Language neutral (site default)"
    )
    self.widgets["language"].mode = z3c.form.interfaces.HIDDEN_MODE
    self.widgets['wysiwyg_editor'].noValueMessage = _(
        u"vocabulary-available-editor-novalue",
        u"Use site default"
    )

default_portrait = '/++theme++ulearn5/assets/images/defaultUser.png'
from zope.interface import alsoProvides
from zope.component import getUtility
from mrs5.max.utilities import IMAXClient
from base5.core.utils import convertSquareImage
import urllib
from OFS.Image import Image
from plone.memoize import ram
from time import time

@ram.cache(lambda *args: time() // (60 * 60))
def getPersonalPortrait(self, id=None, verifyPermission=0):
    """Return a members personal portait.

    Modified from CMFPlone version to URL-quote the member id.
    """
    if not id:
        id = self.getAuthenticatedMember().getId()

    try:
        from plone.protect.interfaces import IDisableCSRFProtection
        alsoProvides(self.request, IDisableCSRFProtection)
    except:
        pass

    maxclient, settings = getUtility(IMAXClient)()
    foto = maxclient.people[id].avatar
    imageUrl = foto.uri + '/large'

    portrait = urllib.urlretrieve(imageUrl)
    an_image = getattr(portrait, 'filename', None)
    if an_image:
        scaled, mimetype = convertSquareImage(portrait[0])
        portrait = Image(id=id, file=scaled, title=id)

        membertool = api.portal.get_tool(name='portal_memberdata')
        membertool._setPortrait(portrait, id)
        import transaction
        transaction.commit()

    membertool = api.portal.get_tool(name='portal_memberdata')
    portrait = membertool._getPortrait(id)
    if isinstance(portrait, str):
        portrait = None

    if portrait is not None:
        from Products.CMFCore.utils import _checkPermission
        if verifyPermission and not _checkPermission('View', portrait):
            # Don't return the portrait if the user can't get to it
            portrait = None
    if portrait is None:
        portal = api.portal.get_tool(name='portal_url').getPortalObject()
        portrait = getattr(portal, default_portrait, None)

    return portrait

import os
import ldap
from ldap.filter import filter_format
from base5.core.directory.views import get_ldap_config

def from_latin1(s):
    """
        Replaces LDAPUserFolder origin from_utf8 to return unicode from
        Credit Andorrap LDAP iso-8859-1 encoded strings
    """
    try:
       return s.decode('utf-8')
    except UnicodeDecodeError:
       return s.decode('latin-1').encode("utf-8")

from ldap.filter import escape_filter_chars

def filter_format(filter_template,assertion_values):
  """
  filter_template
        String containing %s as placeholder for assertion values.
  assertion_values
        List or tuple of assertion values. Length must match
        count of %s in filter_template.
  """
  try:
    return filter_template % tuple(escape_filter_chars(v) for v in assertion_values)
  except UnicodeDecodeError:
    return filter_template % tuple(escape_filter_chars(v).decode('utf-8', errors='ignore') for v in assertion_values)


from plone.memoize.instance import clearafter
from plone.app.workflow.browser.sharing import SharingView

original_update_role_settings = SharingView.update_role_settings


@clearafter
def update_role_settings(self, new_settings, reindex=True):
    def fix_encoding(entry):
        if not isinstance(entry['id'], unicode):
            entry['id'] = entry['id'].decode('utf-8')
        return entry
    settings = [fix_encoding(entry) for entry in new_settings]
    original_update_role_settings(self, settings)


def getGroups(self, dn='*', attr=None, pwd=''):
    """
        returns a list of possible groups from the ldap tree
        (Used e.g. in showgroups.dtml) or, if a DN is passed
        in, all groups for that particular DN.
    """
    ALT_LDAP_URI, ALT_LDAP_DN, ALT_LDAP_PASSWORD, BASEDN, GROUPS_QUERY, USER_GROUPS_QUERY = get_ldap_config()

    if GROUPS_QUERY == '':
        GROUPS_QUERY = '(&(objectClass=groupOfNames))'
    if USER_GROUPS_QUERY == '':
        USER_GROUPS_QUERY = '(&(objectClass=groupOfNames)(member=%s))'

    group_list = []
    no_show = ('Anonymous', 'Authenticated', 'Shared')
    if self._local_groups:
        if dn != '*':
            all_groups_list = self._groups_store.get(dn) or []
        else:
            all_groups_dict = {}
            zope_roles = list(self.valid_roles())
            zope_roles.extend(list(self._additional_groups))

            for role_name in zope_roles:
                if role_name not in no_show:
                    all_groups_dict[role_name] = 1

            all_groups_list = all_groups_dict.keys()

        for group in all_groups_list:
            if attr is None:
                group_list.append((group, group))
            else:
                group_list.append(group)

        group_list.sort()

    else:
        gscope = self._delegate.getScopes()[self.groups_scope]

        if dn != '*':
            group_filter = filter_format(USER_GROUPS_QUERY, (dn,))
        else:
            group_filter = GROUPS_QUERY

        res = self._delegate.search(
            base=self.groups_base,
            scope=gscope,
            filter=group_filter,
            attrs=['cn'],
            bind_dn='',
            bind_pwd='')

        exc = res['exception']
        if exc:
            if attr is None:
                group_list = (('', exc),)
            else:
                group_list = (exc,)
        elif res['size'] > 0:
            res_dicts = res['results']
            for i in range(res['size']):
                dn = res_dicts[i].get('dn')
                try:
                    cn = res_dicts[i]['cn'][0]
                except KeyError:    # NDS oddity
                    cn = self._delegate.explode_dn(dn, 1)[0]

                if attr is None:
                    group_list.append((cn, dn))
                elif attr == 'cn':
                    group_list.append(cn)
                elif attr == 'dn':
                    group_list.append(dn)

    return group_list


def addGroup(self, id, **kw):
    return self.acl_users.manage_addGroup(id)


from base5.core.directory.views import get_create_group_type
from Products.LDAPUserFolder.utils import GROUP_MEMBER_MAP
from Acquisition import aq_parent
def manage_addGroup( self
                   , newgroup_name
                   , newgroup_type='groupOfUniqueNames'
                   , REQUEST=None
                   ):
    """ Add a new group in groups_base """
    newgroup_type = str(get_create_group_type())

    if self._local_groups and newgroup_name:
        add_groups = self._additional_groups

        if newgroup_name not in add_groups:
            add_groups.append(newgroup_name)

        self._additional_groups = add_groups
        msg = 'Added new group %s' % (newgroup_name)

    elif newgroup_name:
        attributes = {}
        attributes['cn'] = [newgroup_name]
        attributes['objectClass'] = ['top', newgroup_type]

        if self._binduid:
            initial_member = self._binduid
        else:
            user = getSecurityManager().getUser()
            try:
                initial_member = user.getUserDN()
            except:
                initial_member = ''

        attributes[GROUP_MEMBER_MAP.get(newgroup_type)] = initial_member

        err_msg = self._delegate.insert( base=self.groups_base
                                       , rdn='cn=%s' % newgroup_name
                                       , attrs=attributes
                                       )
        msg = err_msg or 'Added new group %s' % (newgroup_name)

        # Invalido la RAMCache que hay guardada del ldap
        # La puedo ver en el manage - RAMCache - Statistics
        # /imo/acl_users/ldapexterns
        # con esto fuerzo que se vuelva a llamar al ldap
        # y no muestre solo los grupos del enumerateGroups que estan en el RAMCache
        ldap = aq_parent(self)
        if ldap.ZCacheable_enabled():
            ldap.ZCacheable_invalidate()
    else:
        msg = 'No group name specified'

    if REQUEST:
        return self.manage_grouprecords(manage_tabs_message=msg)
    elif 'Added new group' in msg:
        return True
    else:
        return False

from Products.LDAPUserFolder.utils import VALID_GROUP_ATTRIBUTES
from Products.LDAPUserFolder.utils import guid2string
from Products.LDAPUserFolder.LDAPUserFolder import logger


def searchGroups(self, attrs=(), exact_match=False, **kw):
    """ Look up matching group records based on one or mmore attributes

    This method takes any passed-in search parameters and values as
    keyword arguments and will sort out invalid keys automatically. For
    now it only accepts valid ldap keys, with no translation, as there
    is currently no schema support for groups. The list of accepted
    group attributes is static for now.
    """
    ALT_LDAP_URI, ALT_LDAP_DN, ALT_LDAP_PASSWORD, BASEDN, GROUPS_QUERY, USER_GROUPS_QUERY = get_ldap_config()

    if GROUPS_QUERY == '':
        GROUPS_QUERY = '(&(objectClass=groupOfNames))'
    if USER_GROUPS_QUERY == '':
        USER_GROUPS_QUERY = '(&(objectClass=groupOfNames)(member=%s))'

    groups = []
    groups_base = self.groups_base
    filt_list = []
    search_str = ''

    for (search_param, search_term) in kw.items():
        if search_param not in VALID_GROUP_ATTRIBUTES:
            continue
        if search_param == 'dn':
            groups_base = search_term

        elif search_param == 'objectGUID':
            # we can't escape the objectGUID query piece using filter_format
            # because it replaces backslashes, which we need as a result
            # of guid2string
            groups_base = self.groups_base
            guid = guid2string(search_term)

            if exact_match:
                filt_list.append('(objectGUID=%s)' % guid)
            else:
                filt_list.append('(objectGUID=*%s*)' % guid)

        else:
            # If the keyword arguments contain unknown items we will
            # simply ignore them and continue looking.
            if search_term and exact_match:
                filt_list.append(
                    filter_format(
                        '(%s=%s)',
                        (search_param, search_term)
                    )
                )
            elif search_term:
                filt_list.append(
                    filter_format(
                        '(%s=*%s*)',
                        (search_param, search_term)
                    )
                )
            else:
                filt_list.append('(%s=*)' % search_param)

    if len(filt_list) == 0:
        # We have no useful filter criteria, bail now before bringing the
        # site down with a search that is overly broad.
        res = {'exception': 'No useful filter criteria given'}
        res['size'] = 0

    else:
        oc_filt = GROUPS_QUERY
        filt_list.append(oc_filt)
        search_str = '(&%s)' % ''.join(filt_list)
        res = self._delegate.search(
            base=groups_base,
            scope=self.groups_scope,
            filter=search_str,
            attrs=attrs,
        )

    if res['exception']:
        logger.warn('searchGroups Exception (%s)' % res['exception'])
        msg = 'searchGroups searched "%s"' % search_str
        logger.warn(msg)
        groups = [{
            'dn': res['exception'],
            'cn': 'n/a'
        }]

    elif res['size'] > 0:
        res_dicts = res['results']
        for i in range(res['size']):
            dn = res_dicts[i].get('dn')
            rec_dict = {}

            for key, val in res_dicts[i].items():
                if len(val) > 0:
                    rec_dict[key] = val[0]

            rec_dict['dn'] = dn

            groups.append(rec_dict)

    return groups

import urllib
from ZTUtils.Zope import complex_marshal


def makeQuery(self, **kw):
        return fixed_make_query(**kw)


def fixed_make_query(*args, **kwargs):
    '''Construct a URL query string, with marshalling markup.

    If there are positional arguments, they must be dictionaries.
    They are combined with the dictionary of keyword arguments to form
    a dictionary of query names and values.

    Query names (the keys) must be strings.  Values may be strings,
    integers, floats, or DateTimes, and they may also be lists or
    namespaces containing these types.  Names and string values
    should not be URL-quoted.  All arguments are marshalled with
    complex_marshal().
    '''

    d = {}
    for arg in args:
        d.update(arg)
    d.update(kwargs)

    uq = urllib.quote
    qlist = complex_marshal(d.items())
    for i in range(len(qlist)):
        k, m, v = qlist[i]
        try:
            value = str(v)
        except UnicodeEncodeError:
            value = v.encode('utf-8')

        qlist[i] = '%s%s=%s' % (uq(k), m, uq(value))

    return '&'.join(qlist)


import unicodedata
_marker = []
from BTrees.IIBTree import IITreeSet


def insertForwardIndexEntry(self, entry, documentId):
    """Take the entry provided and put it in the correct place
    in the forward index.

    This will also deal with creating the entire row if necessary.
    """
    try:
            indexRow = self._index.get(entry, _marker)
    except:
            entry = unicodedata.normalize('NFKD', entry.decode('utf-8')).encode('ascii', errors='ignore')
            indexRow = self._index.get(entry, _marker)

    # Make sure there's actually a row there already. If not, create
    # a set and stuff it in first.
    if indexRow is _marker:
        # We always use a set to avoid getting conflict errors on
        # multiple threads adding a new row at the same time
        self._index[entry] = IITreeSet((documentId, ))
        self._length.change(1)
    else:
        try:
            indexRow.insert(documentId)
        except AttributeError:
            # Inline migration: index row with one element was an int at
            # first (before Zope 2.13).
            indexRow = IITreeSet((indexRow, documentId))
            self._index[entry] = indexRow


from ZODB.POSException import ConflictError
from BTrees.Length import Length
from logging import getLogger
LOG = getLogger('Zope.UnIndex')
import sys


def removeForwardIndexEntry(self, entry, documentId):
        """Take the entry provided and remove any reference to documentId
        in its entry in the index.
        """
        try:
            indexRow = self._index.get(entry, _marker)
        except:
            entry = unicodedata.normalize('NFKD', entry.decode('utf-8')).encode('ascii', errors='ignore')
            indexRow = self._index.get(entry, _marker)

        if indexRow is not _marker:
            try:
                indexRow.remove(documentId)
                if not indexRow:
                    del self._index[entry]
                    self._length.change(-1)

            except ConflictError:
                raise

            except AttributeError:
                # index row is an int
                try:
                    del self._index[entry]
                except KeyError:
                    # XXX swallow KeyError because it was probably
                    # removed and then _length AttributeError raised
                    pass
                if isinstance(self.__len__, Length):
                    self._length = self.__len__
                    del self.__len__
                self._length.change(-1)

            except:
                LOG.error('%s: unindex_object could not remove '
                          'documentId %s from index %s.  This '
                          'should not happen.' % (self.__class__.__name__, str(documentId), str(self.id)),
                          exc_info=sys.exc_info())
        else:
            LOG.error('%s: unindex_object tried to retrieve set %s '
                      'from index %s but couldn\'t.  This '
                      'should not happen.' % (self.__class__.__name__, repr(entry), str(self.id)))


from Acquisition import aq_parent, aq_inner, aq_get
from Products.PlonePAS.utils import getGroupsForPrincipal

def getRolesForPrincipal(self, principal, request=None):
        """ See IRolesPlugin.
        """
        roles = set([])
        principal_ids = set([])
        # Some services need to determine the roles obtained from groups
        # while excluding the directly assigned roles.  In this case
        # '__ignore_direct_roles__' = True should be pushed in the request.
        request = aq_get(self, 'REQUEST', None)
        if request is None or \
            not request.get('__ignore_direct_roles__', False):
            principal_ids.add(principal.getId())

        # Some services may need the real roles of an user but **not**
        # the ones he got through his groups. In this case, the
        # '__ignore_group_roles__'= True should be previously pushed
        # in the request.
        plugins = self._getPAS()['plugins']
        if request is None or \
            not request.get('__ignore_group_roles__', False):
            principal_ids.update(getGroupsForPrincipal(principal, plugins,
                                                       request))
        for pid in principal_ids:
            roles.update(self._principal_roles.get(pid.encode('utf-8'), ()))
        return tuple(roles)


from Products.CMFPlone.utils import normalizeString


def update(self):
        self.groupname = getattr(self.request, 'groupname')
        self.gtool = api.portal.get_tool(name='portal_groups')
        self.mtool = api.portal.get_tool(name='portal_membership')
        self.group = self.gtool.getGroupById(self.groupname.decode('utf-8'))
        self.grouptitle = self.group.getGroupTitleOrName() or self.groupname

        self.request.set('grouproles', self.group.getRoles() if self.group else [])
        self.canAddUsers = True
        if 'Manager' in self.request.get('grouproles') and not self.is_zope_manager:
            self.canAddUsers = False

        self.groupquery = self.makeQuery(groupname=self.groupname)
        self.groupkeyquery = self.makeQuery(key=self.groupname)

        form = self.request.form
        submitted = form.get('form.submitted', False)

        self.searchResults = []
        self.searchString = ''
        self.newSearch = False

        if submitted:
            # add/delete before we search so we don't show stale results
            toAdd = form.get('add', [])
            if toAdd:
                if not self.canAddUsers:
                    raise Forbidden

                for u in toAdd:
                    self.gtool.addPrincipalToGroup(u, self.groupname, self.request)
                self.context.plone_utils.addPortalMessage(_(u'Changes made.'))

            toDelete = form.get('delete', [])
            if toDelete:
                for u in toDelete:
                    self.gtool.removePrincipalFromGroup(u, self.groupname, self.request)
                self.context.plone_utils.addPortalMessage(_(u'Changes made.'))

            search = form.get('form.button.Search', None) is not None
            edit = form.get('form.button.Edit', None) is not None and toDelete
            add = form.get('form.button.Add', None) is not None and toAdd
            findAll = form.get('form.button.FindAll', None) is not None and \
                not self.many_users
            # The search string should be cleared when one of the
            # non-search buttons has been clicked.
            if findAll or edit or add:
                form['searchstring'] = ''
            self.searchString = form.get('searchstring', '')
            if findAll or bool(self.searchString):
                self.searchResults = self.getPotentialMembers(self.searchString)

            if search or findAll:
                self.newSearch = True

        self.groupMembers = self.getMembers()


def getMembers(self):
        searchResults = self.gtool.getGroupMembers(self.groupname.decode('utf-8'))

        groupResults = [self.gtool.getGroupById(m) for m in searchResults]
        groupResults.sort(key=lambda x: x is not None and normalizeString(x.getGroupTitleOrName()))

        userResults = [self.mtool.getMemberById(m) for m in searchResults]
        userResults.sort(key=lambda x: x is not None and x.getProperty('fullname') is not None and normalizeString(x.getProperty('fullname')) or '')

        mergedResults = groupResults + userResults
        return filter(None, mergedResults)


def aggregateIndex(self, view_name, req, req_names, local_keys):
    '''
    EL CODIGO ORIGINAL NO TIENE EN CUENTA EL UTF-8 Y DA ERROR EN ASPB
    Returns the index to be used when looking for or inserting
    a cache entry.
    view_name is a string.
    local_keys is a mapping or None.
    '''
    req_index = []
    # Note: req_names is already sorted.
    for key in req_names:
        if req is None:
            val = ''
        else:
            val = req.get(key, '')
        req_index.append((str(key), str(val)))
    if local_keys:
        local_index = []
        for key, val in local_keys.items():
            try:
                local_index.append((str(key), str(val)))
            except:
                pass
        local_index.sort()
    else:
        local_index = ()
    try:
        str_value = (str(view_name.encode('utf-8')), tuple(req_index), tuple(local_index))
    except:
        str_value = (str(view_name), tuple(req_index), tuple(local_index))
    # return (str(view_name.encode('utf-8')), tuple(req_index), tuple(local_index))
    return str_value


def prepareObjectTabs(self, default_tab='view', sort_first=['folderContents']):
    context = self.context
    mt = api.portal.get_tool(name='portal_membership')
    tabs = []
    navigation_root_url = context.absolute_url()

    def _check_allowed(context, request, name):
        """Check, if user has required permissions on view.
        """
        view = getMultiAdapter((context, request), name=name)
        allowed = True
        for perm in view.__ac_permissions__:
            allowed = allowed and mt.checkPermission(perm[0], context)
        return allowed

    if _check_allowed(context, self.request, 'personal-information'):
        tabs.append({
            'title': _('title_personal_information_form',
                       u'Personal Information'),
            'url': navigation_root_url + '/@@personal-information',
            'selected': (self.__name__ == 'personal-information'),
            'id': 'user_data-personal-information',
        })

    if _check_allowed(context, self.request, 'ulearn-personal-preferences'):
        tabs.append({
            'title': _(u'Personal Preferences'),
            'url': navigation_root_url + '/@@ulearn-personal-preferences',
            'selected': (self.__name__ == 'ulearn-personal-preferences'),
            'id': 'user_data-ulearn-personal-preferences',
        })

    member = mt.getAuthenticatedMember()
    if member.canPasswordSet():
        tabs.append({
            'title': _('label_password', u'Password'),
            'url': navigation_root_url + '/@@change-password',
            'selected': (self.__name__ == 'change-password'),
            'id': 'user_data-change-password',
        })
    return tabs


def get_date_options(request):
    from datetime import datetime
    from zope.i18n import translate
    from zope.component import getUtility
    from plone.registry.interfaces import IRegistry
    from Products.CMFPlone.interfaces import IDateAndTimeSchema

    calendar = request.locale.dates.calendars['gregorian']
    registry = getUtility(IRegistry)
    date_tool = registry.forInterface(IDateAndTimeSchema, prefix='plone')
    first_weekday = date_tool.first_weekday
    today = datetime.today()
    return {
        'time': False,
        'date': {
            'firstDay': 0 if first_weekday == 6 else 1,
            'weekdaysFull': [
                calendar.days.get(t, (None, None))[0]
                for t in (7, 1, 2, 3, 4, 5, 6)],
            'weekdaysShort': [
                calendar.days.get(t, (None, None))[1]
                for t in (7, 1, 2, 3, 4, 5, 6)],
            'monthsFull': calendar.getMonthNames(),
            'monthsShort': calendar.getMonthAbbreviations(),
            'selectYears': 200,
            'min': [today.year - 100, 1, 1],
            'max': [today.year + 20, 1, 1],
            'format': translate(
                _('pickadate_date_format', default='mmmm d, yyyy'),
                context=request),
            'placeholder': translate(_('Enter date...'), context=request),
        },
        'today': translate(_(u"Today"), context=request),
        'clear': translate(_(u"Clear"), context=request),
    }


def get_datetime_options(request):
    from plone import api
    from zope.i18n import translate
    from zope.i18nmessageid import MessageFactory
    _ = MessageFactory('plone')

    options = get_date_options(request)
    current_user = api.user.get_current()
    try:
        format_time = current_user.getProperty('format_time')
    except:
        format_time = ''

    # Si el usuario no tiene un formato seleccionado se pone la de por defecto del idioma como lo hace Plone.
    if format_time == '' or format_time == None:
        options['time'] = {
            'format': translate(
                _('pickadate_time_format', default='h:i a'),
                context=request),
            'placeholder': translate(_('Enter time...'), context=request),
        }
        #Hour in 24-hour format with a leading zero
        #format_time = 'HH:i'
    else:
        options['time'] = {
            'format': format_time,
            'placeholder': translate(_('Enter time...'), context=request),
        }
    return options

import unicodedata
from zope import schema

def _setProperty(self, name, value):
    if isinstance(value, set):
        value = list(value)
    if value and isinstance(self.schema[name], schema.Choice):
        if isinstance(value, str):
            value = str(value)
        else:
            value = value.encode('utf-8')
    return self.context.setMemberProperties(
        {name: value}, force_empty=True
    )


from Products.PortalTransforms.transforms.safe_html import decode_htmlentities
import re

CSS_COMMENT = re.compile(r'/\*.*\*/')


def hasScript(s):
    """Dig out evil Java/VB script inside an HTML attribute.
    >>> hasScript('script:evil(1);')
    True
    >>> hasScript('expression:evil(1);')
    True
    >>> hasScript('expression/**/:evil(1);')
    True
    >>> hasScript('http://foo.com/ExpressionOfInterest.doc')
    False
    """
    s = decode_htmlentities(s)
    s = s.replace('\x00', '')
    s = CSS_COMMENT.sub('', s)
    s = ''.join(s.split()).lower()
    # Original code
    # for t in ('script:', 'expression:', 'expression(', 'data:'):
    for t in ('script:', 'expression:', 'expression('):
        if t in s:
            return True
    return False


security = ClassSecurityInfo()

security.declarePrivate('updateGroup')
def updateGroup(self, id, **kw):
    return True


from Products.CMFPlone.PloneBatch import Batch
import json


def ajaxSearchCall(self):
    items = []
    # try:
    #     per_page = int(self.request.form.get('perPage'))
    # except:
    #     per_page = 10
    #
    # Fix results for page in 4
    per_page = 4

    try:
        page = int(self.request.form.get('page'))
    except:
        page = 1

    results = self.results(batch=False, use_content_listing=False)
    batch = Batch(results, per_page, start=(page - 1) * per_page)
    registry = queryUtility(IRegistry)
    length = registry.get('plone.search_results_description_length')
    plone_view = getMultiAdapter(
        (self.context, self.request), name='plone')
    registry = getUtility(IRegistry)
    view_action_types = registry.get(
        'plone.types_use_view_action_in_listings', [])
    for item in batch:
        url = item.getURL()
        if item.portal_type in view_action_types:
            url = '%s/view' % url
        items.append({
            'id': item.UID,
            'title': item.Title,
            'description': plone_view.cropText(item.Description, length),
            'url': url,
            'state': item.review_state if item.review_state else None,
        })
    return json.dumps({
        'total': len(results),
        'items': items
    })


from plone.app.content.browser.contents.workflow import WorkflowActionView


def workflowActionViewCall(self):
    self.pworkflow = api.portal.get_tool(name='portal_workflow')
    self.putils = api.portal.get_tool(name='plone_utils')
    self.transition_id = self.request.form.get('transition', None)
    self.comments = self.request.form.get('comments', '')
    self.recurse = self.request.form.get('recurse', 'no') == 'yes'
    if self.request.form.get('render') == 'yes':
        # asking for render information
        selection = self.get_selection()
        catalog = api.portal.get_tool(name='portal_catalog')
        brains = catalog(UID=selection, show_inactive=True)
        transitions = []

        current = api.user.get_current()
        lang = current.getProperty('language')
        for brain in brains:
            obj = brain.getObject()
            for transition in self.pworkflow.getTransitionsFor(obj):
                tdata = {
                    'id': transition['id'],
                    'title': self.context.translate(transition['name'], domain='ulearn', target_language=lang)
                }
                if tdata not in transitions:
                    transitions.append(tdata)
        return self.json({
            'transitions': transitions
        })
    else:
        return super(WorkflowActionView, self).__call__()
