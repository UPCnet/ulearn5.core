# -*- coding: utf-8 -*-
from AccessControl import Unauthorized
from DateTime.DateTime import DateTime
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFPlone.interfaces.constrains import ISelectableConstrainTypes
from Products.CMFPlone.utils import safe_unicode
from Products.statusmessages.interfaces import IStatusMessage
from ZPublisher.HTTPRequest import FileUpload

from five import grok
from hashlib import sha1
from plone import api
from plone.dexterity.content import Container
from plone.dexterity.interfaces import IDexterityContent
from plone.dexterity.utils import createContentInContainer
from plone.directives import form
from plone.indexer import indexer
from plone.memoize.view import memoize_contextless
from plone.namedfile.field import NamedBlobImage
from plone.portlets.interfaces import IPortletManager
from plone.portlets.interfaces import IPortletRetriever
from plone.registry.interfaces import IRegistry
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from repoze.catalog.query import Eq
from repoze.catalog.query import Or
from souper.interfaces import ICatalogFactory
from souper.soup import NodeAttributeIndexer
from souper.soup import Record
from souper.soup import get_soup
from z3c.form import button
from zope import schema
from zope.component import adapts
from zope.component import getMultiAdapter
from zope.component import getUtility
from zope.component import queryUtility
from zope.component.hooks import getSite
from zope.container.interfaces import INameChooser
from zope.container.interfaces import IObjectAddedEvent
from zope.event import notify
from zope.globalrequest import getRequest
from zope.interface import Interface
from zope.interface import Invalid
from zope.interface import alsoProvides
from zope.interface import implementer
from zope.interface import implements
from zope.lifecycleevent import ObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectModifiedEvent
from zope.lifecycleevent.interfaces import IObjectRemovedEvent
from zope.schema.interfaces import IContextSourceBinder
from zope.schema.vocabulary import SimpleVocabulary
from zope.security import checkPermission

from base5.core.adapters.favorites import IFavorite
from base5.core.adapters.notnotifypush import INotNotifyPush
from base5.core.utils import json_response
from mrs5.max.utilities import IHubClient
from mrs5.max.utilities import IMAXClient
from ulearn5.core import _
from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.interfaces import IDXFileFactory
from ulearn5.core.interfaces import IDocumentFolder
from ulearn5.core.interfaces import IEventsFolder
from ulearn5.core.interfaces import INewsItemFolder
from ulearn5.core.interfaces import IPhotosFolder
from ulearn5.core.utils import is_activate_owncloud, is_activate_externalstorage, is_activate_etherpad
from ulearn5.core.widgets.select2_maxuser_widget import Select2MAXUserInputFieldWidget
from ulearn5.core.widgets.select2_user_widget import SelectWidgetConverter
from ulearn5.core.widgets.terms_widget import TermsFieldWidget
from ulearn5.owncloud.api.owncloud import Client
from ulearn5.owncloud.api.owncloud import HTTPResponseError
from ulearn5.owncloud.api.owncloud import OCSResponseError
from ulearn5.owncloud.utilities import IOwncloudClient
from ulearn5.owncloud.api.owncloud import Client, HTTPResponseError, OCSResponseError
from DateTime.DateTime import DateTime
from plone.app.layout.navigation.root import getNavigationRootObject
from ulearn5.owncloud.utils import get_domain
from ulearn5.owncloud.utils import update_owncloud_permission
from z3c.form.interfaces import IAddForm, IEditForm
from z3c.form.browser.checkbox import SingleCheckBoxFieldWidget
from ulearn5.core.widgets.single_checkbox_notify_email_widget import SingleCheckBoxNotifyEmailFieldWidget

from plone.memoize import ram
from time import time

import ast
import json
import logging
import mimetypes


logger = logging.getLogger(__name__)
VALID_COMMUNITY_ROLES = ['reader', 'writer', 'owner']

OPEN_PERMISSIONS = dict(read='subscribed',
                        write='subscribed',
                        subscribe='public',
                        unsubscribe='public')

CLOSED_PERMISSIONS = dict(read='subscribed',
                          write='restricted',
                          subscribe='restricted',
                          unsubscribe='public')

ORGANIZATIVE_PERMISSIONS = dict(read='subscribed',
                                write='restricted',
                                subscribe='restricted',
                                unsubscribe='restricted')

@ram.cache(lambda *args: time() // (60 * 60))
def packages_installed():
    qi_tool = api.portal.get_tool(name='portal_quickinstaller')
    installed = [p['id'] for p in qi_tool.listInstalledProducts()]
    return installed

class CommunityForbiddenAction(Exception):
    """ Exception to be raised when trying to execute an action that
        is forbidden in the context being executed """

# DEFINICIO DE COMUNITAT


@grok.provider(IContextSourceBinder)
def availableCommunityTypes(context):
    terms = []

    user_roles = api.user.get_roles()

    if 'CC open' in user_roles or \
       'WebMaster' in user_roles or \
       'Manager' in user_roles:
        terms.append(SimpleVocabulary.createTerm(u'Open', 'open', _(u'Open')))

    if 'CC closed' in user_roles or \
       'WebMaster' in user_roles or \
       'Manager' in user_roles:
        terms.append(SimpleVocabulary.createTerm(u'Closed', 'closed', _(u'Closed')))

    if 'CC organizative' in user_roles or \
       'WebMaster' in user_roles or \
       'Manager' in user_roles:
        terms.append(SimpleVocabulary.createTerm(u'Organizative', 'organizative', _(u'Organizative')))

    return SimpleVocabulary(terms)


@grok.provider(IContextSourceBinder)
def communityActivityViews(context):
    terms = []

    terms.append(SimpleVocabulary.createTerm(u'Darreres activitats', 'darreres_activitats', _(u'Darreres activitats')))
    terms.append(SimpleVocabulary.createTerm(u'Activitats mes valorades', 'activitats_mes_valorades', _(u'Activitats mes valorades')))
    terms.append(SimpleVocabulary.createTerm(u'Activitats destacades', 'activitats_destacades', _(u'Activitats destacades')))

    return SimpleVocabulary(terms)

@grok.provider(IContextSourceBinder)
def communityTabViews(context):
    terms = []

    terms.append(SimpleVocabulary.createTerm(u'Activity', 'activity', _(u'Activity')))
    terms.append(SimpleVocabulary.createTerm(u'Documents', 'documents', _(u'Documents')))

    return SimpleVocabulary(terms)


@grok.provider(IContextSourceBinder)
def communityTypeNotify(context):
    terms = []

    terms.append(SimpleVocabulary.createTerm(u'Automatic', 'automatic', _(u'Automatic')))
    terms.append(SimpleVocabulary.createTerm(u'Manual', 'manual', _(u'Manual')))

    return SimpleVocabulary(terms)

# @grok.provider(IContextSourceBinder)
# def getCommunityTab(self):
#     return self.portal_url()

def isChecked(value):
    if not value:
        raise Invalid(_(u'falta_condicions', default=u"Es necessari acceptar les condicions d'us i privacitat per crear una comunitat."))
    return True


class ICommunity(form.Schema):
    """ A manageable community
    """

    title = schema.TextLine(
        title=_(u'Nom'),
        description=_(u'Nom de la comunitat'),
        required=True
    )

    description = schema.Text(
        title=_(u'Descripcio'),
        description=_(u'La descripcio de la comunitat'),
        required=False
    )

    form.mode(IEditForm, community_type='hidden')
    community_type = schema.Choice(
        title=_(u'Tipus de comunitat'),
        description=_(u'community_type_description'),
        source=availableCommunityTypes,
        required=True,
        default=u'Closed'
    )

    activity_view = schema.Choice(
        title=_(u'activity_view'),
        description=_(u'help_activity_view'),
        source=communityActivityViews,
        required=True,
        default=u'Darreres activitats')

    tab_view = schema.Choice(
        title=_(u'tab_view'),
        description=_(u'help_tab_view'),
        source=communityTabViews,
        required=True,
        default=u'Activity')

    form.omitted('readers', 'subscribed', 'owners')
    form.widget(readers=Select2MAXUserInputFieldWidget)
    readers = schema.List(
        title=_(u'Readers'),
        description=_(u'Subscribed people with read-only permissions'),
        value_type=schema.TextLine(),
        required=False,
        missing_value=[],
        default=[])

    # We maintain the subscribed field for backwards compatibility,
    # understanding that it refers to users with read/write permissions
    form.widget(subscribed=Select2MAXUserInputFieldWidget)
    subscribed = schema.List(
        title=_(u'Editors'),
        description=_(u'Subscribed people with editor permissions'),
        value_type=schema.TextLine(),
        required=False,
        missing_value=[],
        default=[])

    form.widget(owners=Select2MAXUserInputFieldWidget)
    owners = schema.List(
        title=_(u'Owners'),
        description=_(u'Subscribed people with owner permissions'),
        value_type=schema.TextLine(),
        required=False,
        missing_value=[],
        default=[])

    image = NamedBlobImage(
        title=_(u'Imatge'),
        description=_(u'Imatge que defineix la comunitat'),
        required=False,
    )

    twitter_hashtag = schema.TextLine(
        title=_(u'Twitter hashtag'),
        description=_(u'hashtag_help'),
        required=False
    )

    show_news = schema.Bool(
        title=_(u'Show news'),
        description=_(u'Show news in the central area of the main community page'),
        required=False,
        default=True
    )

    show_events = schema.Bool(
        title=_(u'Show events'),
        description=_(u'Show events in the central area of the main community page.'),
        required=False,
        default=True
    )

    notify_activity_via_push = schema.Bool(
        title=_(u'Notify activity via push'),
        description=_(u'notify_activity_via_push_help'),
        required=False
    )

    notify_activity_via_push_comments_too = schema.Bool(
        title=_(u'Notify activity and comments via push'),
        description=_(u'help_notify_activity_via_push_comments_too'),
        required=False
    )

    form.widget(notify_activity_via_mail=SingleCheckBoxNotifyEmailFieldWidget)
    notify_activity_via_mail = schema.Bool(
        title=_(u'Notify activity via mail'),
        description=_(u'notify_activity_via_mail_help'),
        required=False
    )

    type_notify = schema.Choice(
        title=_(u'type_notify'),
        description=_(u'help_type_notify'),
        source=communityTypeNotify,
        required=True,
        default=u'Automatic')

    form.mode(IAddForm, mails_users_community_lists='hidden')
    form.mode(IEditForm, mails_users_community_lists='hidden')
    mails_users_community_lists = schema.Text(
        title=_(u'Users comunnity lists'),
        description=_(u'users_community_lists_help'),
        required=False
    )

    form.mode(IAddForm, mails_users_community_black_lists='hidden')
    form.mode(IEditForm, mails_users_community_black_lists='hidden')
    mails_users_community_black_lists = schema.Text(
        title=_(u'Users comunnity black lists'),
        description=_(u'users_community_black_lists_help'),
        required=False
    )

    distribution_lists = schema.Text(
        title=_(u'Distribution lists'),
        description=_(u'distribution_lists_help'),
        required=False
    )

    form.mode(IAddForm, terms='hidden')
    form.mode(IEditForm, terms='hidden')
    form.widget(terms=TermsFieldWidget)
    terms = schema.Bool(
        title=_(u'title_terms_of_user'),
        description=_(u'description_terms_of_user'),
        constraint=isChecked
    )



# INTERFICIES QUE POT IMPLEMENTAR UNA COMUNITAT


class ICommunityACL(Interface):
    """ Helper to retrieve the community ACL safely by adapting any ICommunity """


class IInitializedCommunity(Interface):
    """ A Community that has been succesfully initialized """


class ICommunityTyped(Interface):
    """ The adapter for the ICommunity It would adapt the Community instances in
        order to have a centralized way of dealing with community types and the
        common processes with them. """


class ICommunityInitializeAdapter(Interface):
    """ The marker interface for initialize community adapter used for a especific
        folders and templates. The idea is to have a default (core) action and
        then other that override the default one using IBrowserLayer """


#@grok.implementer(ICommunityACL)
#@grok.adapter(ICommunity)
class GetCommunityACL(object):
    implements(ICommunityACL)
    adapts(ICommunity)

    def __init__(self, context):
        self.context = context

    def __call__(self):
        portal = api.portal.get()
        soup = get_soup('communities_acl', portal)
        gwuuid = IGWUUID(self.context).get()
        records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

        if records:
            return records[0]
        else:
            return None

# METODES COMUNS PER A TOTS ELS TIPUS DE COMUNITATS (PARAMETRES MAX)


class CommunityAdapterMixin(object):
    """ Common methods for community adapters """

    # Role that will be given to a user when auto-subscribing in allowed communities
    # As by default a community adapter allows auto-ubscription, if you want to disable it
    # for a community adapter, you have to provide an subscribe_user method that disallows it.
    subscription_community_role = None

    # Roles that will be available as valid community roles,
    # and so displayed in the edtiacl view
    available_roles = ['reader', 'writer', 'owner']

    def __init__(self, context):
        self.context = context
        self.get_max_client()
        self.get_hub_client()

        # Determine the value for notifications
        if self.context.notify_activity_via_push and self.context.notify_activity_via_push_comments_too:
            self.max_notifications = 'comments'
        elif not self.context.notify_activity_via_push and self.context.notify_activity_via_push_comments_too:
            self.max_notifications = 'comments'
        elif self.context.notify_activity_via_push and not self.context.notify_activity_via_push_comments_too:
            self.max_notifications = 'posts'
        elif not self.context.notify_activity_via_push and not self.context.notify_activity_via_push_comments_too:
            self.max_notifications = False

    def get_max_client(self):
        self.maxclient, self.settings = getUtility(IMAXClient)()
        self.maxclient.setActor(self.settings.max_restricted_username)
        self.maxclient.setToken(self.settings.max_restricted_token)

    def get_hub_client(self):
        self.hubclient, settings = getUtility(IHubClient)()
        self.hubclient.setActor(settings.max_restricted_username)
        self.hubclient.setToken(settings.max_restricted_token)

    def create_max_context(self):
        """ Add context for the community on MAX server given a set of
            properties like context permissions and notifications.
        """
        self.maxclient.contexts.post(
            url=self.context.absolute_url(),
            displayName=self.context.title,
            permissions=self.max_permissions,
            notifications=self.max_notifications,
            # Include notify=False
        )

    def set_initial_max_metadata(self):
        # Update twitter hashtag
        self.maxclient.contexts[self.context.absolute_url()].put(
            twitterHashtag=self.context.twitter_hashtag
        )

        # Update community tag
        self.maxclient.contexts[self.context.absolute_url()].tags.put(data=['[COMMUNITY]'])

    def set_initial_subscription(self, acl):
        self.maxclient.people[self.context.Creator()].subscriptions.post(object_url=self.context.absolute_url())
        self.update_acl(acl)

        for permission in self.community_role_mappings['owner']['max']:
            self.maxclient.contexts[self.context.absolute_url()].permissions[self.context.Creator()][permission].put()

        self.update_hub_subscriptions()

    def update_community_type(self):
        # Guard in case the update could already be made by other means
        context_current_info = self.maxclient.contexts[self.context.absolute_url()].get()
        should_update = False
        for key in self.max_permissions:
            if self.max_permissions[key] != context_current_info['permissions'][key]:
                should_update = True
        if should_update:
            properties_to_update = dict(permissions=self.max_permissions)
            self.maxclient.contexts[self.context.absolute_url()].put(**properties_to_update)

        # Update the community_type field
        self.context.community_type = self.get_community_type_adapter()

        # and related permissions
        self.set_plone_permissions(self.get_acl())

        self.context.reindexObject()

    def delete_community_all(self):
        self.delete_max_context()
        self.delete_acl()

    def get_acl(self):
        return ICommunityACL(self.context)().attrs.get('acl', '')

    def update_acl(self, acl):
        gwuuid = IGWUUID(self.context).get()
        portal = api.portal.get()
        soup = get_soup('communities_acl', portal)

        records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

        # Save ACL into the communities_acl soup
        if records:
            acl_record = records[0]
        else:
            # The community isn't indexed in the acl catalog yet, so do it now.
            record = Record()
            record.attrs['path'] = '/'.join(self.context.getPhysicalPath())
            record.attrs['gwuuid'] = gwuuid
            record.attrs['hash'] = sha1(self.context.absolute_url()).hexdigest()
            record_id = soup.add(record)
            acl_record = soup.get(record_id)

        acl_record.attrs['groups'] = [g['id'] for g in acl.get('groups', []) if g.get('id', False)]
        acl_record.attrs['acl'] = acl

        soup.reindex(records=[acl_record])

    def delete_acl(self):
        """ In case that we delete the community, delete its ACL record. """
        gwuuid = IGWUUID(self.context).get()
        portal = api.portal.get()
        soup = get_soup('communities_acl', portal)

        records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

        if records:
            del soup[records[0]]

    def remove_acl_atomic(self, username):
        acl = self.get_acl()

        for user in acl['users']:
            if user['id'] == username:
                acl['users'].remove(user)

        self.update_acl(acl)

    def update_acl_atomic(self, username, role):
        """ This method is used when it is required to perform an atomic (single
            user) acl update to a community. It supports either adding a new
            user and updating an existing one.
        """
        acl = self.get_acl()
        new_user_acl = dict(id=username, displayName=u'', role=role)

        updating = False
        for user in acl['users']:
            if user['id'] == username:
                # We are updating
                user['role'] = role
                updating = True

        if not updating:
            # We are adding
            acl['users'].append(new_user_acl)

        self.update_acl(acl)

    def update_hub_subscriptions(self):
        max_permission_mappings = {role: mappings['max'] for role, mappings in self.community_role_mappings.items()}
        portal = api.portal.get()
        registry = queryUtility(IRegistry)
        ulearn_settings = registry.forInterface(IUlearnControlPanelSettings)
        if ulearn_settings.url_site != None and ulearn_settings.url_site != '':
            url_site = ulearn_settings.url_site
        else:
            url_site = portal.absolute_url()
        subscribe_request = {}
        subscribe_request['component'] = dict(type='communities', id=url_site)
        subscribe_request['permission_mapping'] = max_permission_mappings
        subscribe_request['ignore_grants_and_vetos'] = True
        subscribe_request['context'] = url_site + '/' + '/'.join(self.context.absolute_url().split('/')[-1:])
        subscribe_request['acl'] = self.get_acl()

        self.hubclient.api.domains[self.settings.domain].services['syncacl'].post(**subscribe_request)

    def add_max_subscription_atomic(self, username):
        """ Used in auto-subscribe an user to an Open community. """
        self.maxclient.people[username].subscriptions.post(object_url=self.context.absolute_url())

    def remove_max_subscription_atomic(self, username):
        """ Used in unsubscribe an user to an Open or Closed community. """
        self.maxclient.people[username].subscriptions[self.context.absolute_url()].delete()

    def update_max_context(self):
        # Get current MAX context information
        context_current_info = self.maxclient.contexts[self.context.absolute_url()].get()

        # collect updated properties
        properties_to_update = {}
        if context_current_info:
            if context_current_info.get('twitterHashtag', None) != self.context.twitter_hashtag:
                properties_to_update['twitterHashtag'] = self.context.twitter_hashtag

            if context_current_info.get('displayName', '') != self.context.title:
                properties_to_update['displayName'] = self.context.title

            if context_current_info.get('notifications', '') != self.max_notifications:
                properties_to_update['notifications'] = self.max_notifications

        # update context properties that have changed
        if properties_to_update:
            self.maxclient.contexts[self.context.absolute_url()].put(**properties_to_update)

    def delete_max_context(self):
        self.maxclient.contexts[self.context.absolute_url()].delete()

    def set_plone_permissions(self, acl, changed=False):
        """ Set the Plone local roles given the acl. Shameless ripped off from
            sharing.py in p.a.workflow
        """
        acl_user_and_groups = acl.get('users', []) + acl.get('groups', [])

        # First, get a list with the current principals assigned to Plone ACL
        # and exclude 'AuthenticatedUsers'
        current_acl_principals = [p[0] for p in self.context.get_local_roles()]
        if 'AuthenticatedUsers' in current_acl_principals:
            current_acl_principals.remove('AuthenticatedUsers')

        member_ids_to_clear = frozenset(current_acl_principals) - frozenset([p['id'] for p in acl_user_and_groups])
        # Search for users no longer in ACL and sanitize the list, just in case
        user_and_groups = [p for p in acl_user_and_groups if p.get('id', False) and p.get('role', False) and p.get('role', '') in VALID_COMMUNITY_ROLES]

        for principal in user_and_groups:
            user_id = principal['id']
            existing_roles = frozenset(self.context.get_local_roles_for_userid(userid=user_id))

            # Determine which Plone Roles we have to use base on the principal's copmmunity role
            # The mapping of community role --> plone roles is defined per-community in the adapter
            fallback_default = dict(max=['read'], plone=['Reader'])
            role_mappings = self.community_role_mappings
            selected_roles = frozenset(role_mappings.get(principal['role'], fallback_default).get('plone'))

            managed_roles = frozenset(['Reader', 'Contributor', 'Editor', 'Owner'])
            relevant_existing_roles = managed_roles & existing_roles

            # If, for the managed roles, the new set is the same as the
            # current set we do not need to do anything.
            if relevant_existing_roles == selected_roles:
                continue

            # We will remove those roles that we are managing and which set
            # on the context, but which were not selected
            to_remove = relevant_existing_roles - selected_roles

            # Leaving us with the selected roles, less any roles that we
            # want to remove
            wanted_roles = (selected_roles | existing_roles) - to_remove

            # take away roles that we are managing, that were not selected
            # and which were part of the existing roles

            if wanted_roles:
                self.context.manage_setLocalRoles(user_id, list(wanted_roles))
                changed = True
            elif existing_roles:
                member_ids_to_clear.append(user_id)

        if member_ids_to_clear:
            self.context.manage_delLocalRoles(userids=member_ids_to_clear)
            changed = True

        if changed:
            self.context.reindexObjectSecurity()

    def unsubscribe_user(self, user_id):
        """
            Removes a user both from max and plone, updating related permissions
        """
        self.remove_max_subscription_atomic(user_id)

        # Remove from acl
        self.remove_acl_atomic(user_id)

        acl = self.get_acl()
        # Finally, we update the plone permissions
        self.set_plone_permissions(acl)

        if is_activate_owncloud(self.context):
            update_owncloud_permission(self.context, acl)

        # Unfavorite
        IFavorite(self.context).remove(user_id)

        INotNotifyPush(self.context).remove(user_id)


        # Remove mail user to mails_users_community_lists in community
        if ((self.context.notify_activity_via_mail == True) and (self.context.type_notify == 'Automatic')):
            if self.context.mails_users_community_lists != None:
                if api.user.get(user_id).getProperty('email') in self.context.mails_users_community_lists:
                    self.context.mails_users_community_lists.pop(api.user.get(user_id).getProperty('email'))

            if self.context.mails_users_community_black_lists is None:
                self.context.mails_users_community_black_lists = {}
            elif not isinstance(self.context.mails_users_community_black_lists, dict):
                self.context.mails_users_community_black_lists = ast.literal_eval(self.context.mails_users_community_black_lists)

            if user_id in self.context.mails_users_community_black_lists:
                self.context.mails_users_community_black_lists.pop(user_id)

        self.context.reindexObject()

    def subscribe_user(self, user_id):
        """
            Adds a user both to max and plone, updating related permissions
        """
        #     community.community_type == u'Open' and \
        # 'Reader' in api.user.get_roles(obj=self.context):

        # Subscribe to context
        self.add_max_subscription_atomic(user_id)

        INotNotifyPush(self.context).add(user_id)

        # For this use case, the user is able to auto-subscribe to the
        # community with write permissions
        self.update_acl_atomic(user_id, self.subscription_community_role)

        acl = self.get_acl()
        # Finally, we update the plone permissions
        self.set_plone_permissions(acl)
        if is_activate_owncloud(self.context):
            update_owncloud_permission(self.context, acl)

        # Add mail user to mails_users_community_lists in community
        if ((self.context.notify_activity_via_mail == True) and (self.context.type_notify == 'Automatic')):
            mail = api.user.get(user_id).getProperty('email')
            if mail != '' and mail != None:
                if self.context.mails_users_community_lists == None:
                    self.context.mails_users_community_lists = []
                self.context.mails_users_community_lists.append(mail)
        self.context.reindexObject()

    def subscribe_user_push(self, user_id):
        self.maxclient.contexts[sha1(self.context.absolute_url()).hexdigest()].subscriptionpush[user_id].delete()

    def unsubscribe_user_push(self, user_id):
        self.maxclient.contexts[sha1(self.context.absolute_url()).hexdigest()].unsubscriptionpush[user_id].post()

    def update_mails_users(self, obj, acl):
        """
            Add mails users to mails_users_community_lists and mails_users_community_black_lists in community
        """
        mails_users = []
        if 'users' in acl:
            for user in acl['users']:
                # Esto lo hago para los usuarios que no se han validado y no estan en el MemberData
                if api.user.get(user['id']) != None:
                    mail = api.user.get(user['id']).getProperty('email')
                    if mail != '' and mail != None and mail not in mails_users:
                        mails_users.append(mail)


        if 'groups' in acl:
            for group in acl['groups']:
                users = api.user.get_users(groupname=group['id'])
                for user in users:
                    if api.user.get(user.id) != None:
                        mail = api.user.get(user.id).getProperty('email')
                        if (mail != '' and mail != None) and mail not in mails_users:
                            mails_users.append(mail)

        obj.mails_users_community_lists = mails_users

        if obj.mails_users_community_black_lists is None:
            obj.mails_users_community_black_lists = {}
        elif not isinstance(obj.mails_users_community_black_lists, dict):
            obj.mails_users_community_black_lists = ast.literal_eval(obj.mails_users_community_black_lists)

        for userid in obj.mails_users_community_black_lists.keys():
            user = api.user.get(userid)
            if user is not None:
                mail = user.getProperty('email')
                if (mail != '' and mail is not None):
                    obj.mails_users_community_black_lists[userid] = mail

        obj.reindexObject()


class OrganizativeCommunity(CommunityAdapterMixin):
    """ Named adapter for the organizative communities """
    implements(ICommunityTyped)
    adapts(ICommunity, Interface)

    def __init__(self, context, request):
        super(OrganizativeCommunity, self).__init__(context)
        self.max_permissions = ORGANIZATIVE_PERMISSIONS
        self.community_role_mappings = dict(
            reader={
                'plone': ['Reader'],
                'max': ['read']
            },
            writer={
                'plone': ['Reader', 'Contributor', 'Editor'],
                'max': ['read', 'write']
            },
            owner={
                'plone': ['Reader', 'Contributor', 'Editor', 'Owner'],
                'max': ['read', 'write', 'unsubscribe', 'flag', 'invite', 'kick', 'delete']
            }
        )

    def unsubscribe_user(self, user_id):
        raise CommunityForbiddenAction('Unsubscription from organizative community forbidden.')

    def subscribe_user(self, user_id):
        raise CommunityForbiddenAction('Subscription to organizative community forbidden.')

    def set_plone_permissions(self, acl, changed=False):
        if self.context.get_local_roles_for_userid(userid='AuthenticatedUsers'):
            self.context.manage_delLocalRoles(['AuthenticatedUsers'])
            changed = True

        super(OrganizativeCommunity, self).set_plone_permissions(acl, changed)

    def get_community_type_adapter(self):
        return 'Organizative'


class OpenCommunity(CommunityAdapterMixin):
    """ Named adapter for the open communities """
    implements(ICommunityTyped)
    adapts(ICommunity, Interface)

    def __init__(self, context, request):
        super(OpenCommunity, self).__init__(context)
        self.max_permissions = OPEN_PERMISSIONS
        self.subscription_community_role = 'writer'
        self.community_role_mappings = dict(
            reader={
                'plone': ['Reader'],
                'max': ['read', 'unsubscribe']
            },
            writer={
                'plone': ['Reader', 'Contributor', 'Editor'],
                'max': ['read', 'write', 'unsubscribe']
            },
            owner={
                'plone': ['Reader', 'Contributor', 'Editor', 'Owner'],
                'max': ['read', 'write', 'unsubscribe', 'flag', 'invite', 'kick', 'delete']
            }
        )

    def set_plone_permissions(self, acl, changed=False):
        if self.context.get_local_roles_for_userid(userid='AuthenticatedUsers'):
            self.context.manage_delLocalRoles(['AuthenticatedUsers'])
            changed = True
        # if not self.context.get_local_roles_for_userid(userid='AuthenticatedUsers'):
        #     self.context.manage_setLocalRoles('AuthenticatedUsers', ['Reader'])
        #     changed = True

        super(OpenCommunity, self).set_plone_permissions(acl, changed)

    def get_community_type_adapter(self):
        return 'Open'


class ClosedCommunity(CommunityAdapterMixin):
    """ Named adapter for the closed communities """
    implements(ICommunityTyped)
    adapts(ICommunity, Interface)

    def __init__(self, context, request):
        super(ClosedCommunity, self).__init__(context)
        self.max_permissions = CLOSED_PERMISSIONS
        self.community_role_mappings = dict(
            reader={
                'plone': ['Reader'],
                'max': ['read', 'unsubscribe']
            },
            writer={
                'plone': ['Reader', 'Contributor', 'Editor'],
                'max': ['read', 'write', 'unsubscribe']
            },
            owner={
                'plone': ['Reader', 'Contributor', 'Editor', 'Owner'],
                'max': ['read', 'write', 'unsubscribe', 'flag', 'invite', 'kick', 'delete']
            }
        )

    def set_plone_permissions(self, acl, changed=False):
        if self.context.get_local_roles_for_userid(userid='AuthenticatedUsers'):
            self.context.manage_delLocalRoles(['AuthenticatedUsers'])
            changed = True

        super(ClosedCommunity, self).set_plone_permissions(acl, changed)

    def subscribe_user(self, user_id):
        raise CommunityForbiddenAction('Subscription to closed community forbidden.')

    def get_community_type_adapter(self):
        return 'Closed'


class Community(Container):
    implements(ICommunity)

    def adapted(self, request=None, name=None):
        effective_name = self.community_type if name is None else name
        request = request if request is not None else getRequest()
        adapter = getMultiAdapter((self, request), ICommunityTyped, name=effective_name)
        return adapter

    def canSetDefaultPage(self):
        """
        Override BrowserDefaultMixin because default page stuff doesn't make
        sense for topics.
        """
        return False


class View(grok.View):
    grok.context(ICommunity)
    grok.require('zope2.View')

    def canEditCommunity(self):
        return checkPermission('cmf.RequestReview', self.context)

    @memoize_contextless
    def portal_url(self):
        return self.portal().absolute_url()

    @memoize_contextless
    def portal(self):
        return getSite()

    def is_user_subscribed(self):
        pm = api.portal.get_tool(name='portal_membership')
        current_user = pm.getAuthenticatedMember().getUserName()
        return current_user in self.context.readers or \
            current_user in self.context.subscribed or \
            current_user in self.context.owners

    def show_community_open_but_not_subscribed(self):
        if self.context.community_type == 'Open' and \
           not self.is_user_subscribed():
            return True
        else:
            return False

    def show_community_open_subscribed_readonly(self):
        """ DEPRECATED: This use case happens when given a closed community and then is
            converted to an open one, the users with reader role stays with that
            role, but are allowed to 'upgrade' it to writer.
        """
        pm = api.portal.get_tool(name='portal_membership')
        current_user = pm.getAuthenticatedMember().getUserName()
        if self.context.community_type == 'Open' and \
           current_user in self.context.readers and \
           current_user not in self.context.owners and \
           current_user not in self.context.subscribed:
            return True
        else:
            return False

    def isDisplayedChat(self):
        columns = ['plone.leftcolumn', 'plone.rightcolumn']
        for column in columns:
            managerColumn = getUtility(IPortletManager, name=column)
            retriever = getMultiAdapter((self.context, managerColumn), IPortletRetriever)
            portlets = retriever.getPortlets()
            for portlet in portlets:
                if portlet['name'] == 'maxuichat':
                    return False
        return True


class UpdateUserAccessDateTime(grok.View):
    grok.context(ICommunity)

    @json_response
    def render(self):
        """ Quan accedeixes a la comunitat, actualitza la data d'accès de l'usuari
            a la comunitat i per tant, el comptador de pendents queda a 0. """
        portal = api.portal.get()
        current_user = api.user.get_current()
        user_community = current_user.id + '_' + self.context.id
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

        return dict(message='Done', status_code=200)


class EditACL(grok.View):
    grok.context(ICommunity)

    def get_gwuuid(self):
        return IGWUUID(self.context).get()

    def get_acl(self):
        acl = ICommunityACL(self.context)().attrs.get('acl', '')
        # Search for users with missing or empty displayname
        query_missing_displaynames = [Eq('username', user.get('id')) for user in acl['users'] if not user.get('displayName', '')]
        if query_missing_displaynames:
            # Generate a query to find properties from all users
            # that lacks the displayname
            portal = api.portal.get()
            soup = get_soup('user_properties', portal)
            query_missing_displaynames = Or(*query_missing_displaynames)
            results = soup.query(query_missing_displaynames)

            # Store all the found displaynames indexed by user
            displaynames = {}
            for result in results:
                try:
                    displaynames[result.attrs['username']] = result.attrs['fullname']
                except:
                    pass

            # Update the acl list with recovered displaynames from soup
            for user in acl['users']:
                userid = user.get('id')
                if userid in displaynames:
                    user['displayName'] = displaynames[userid]

        return json.dumps(acl)

    def get_acl_roles(self):
        roles = self.context.adapted().available_roles
        return [{'id': role, 'header': role.upper()} for role in roles]

    def get_acl_roles_json(self):
        roles = self.context.adapted().available_roles
        return json.dumps([{'id': role, 'header': role.upper()} for role in roles])


class NotifyAtomicChange(grok.View):
    """ This is a context endpoint for notify the context with external changes
        to the context. This changes can be originated for example, by an user
        changing the context programatically via the maxclient or via the
        uLearnHub user interface.

        The MAX server will notify the change to this endpoint using the form:

            {
              "action": "", // one of subscribe, unsubscribe, change_permissions
              "username": "victor.fernandez",
              "subscription": {
                "hash": "93717fe74ad7cdee87312f98863de2c4cb9c98a2",
                "url": "https://max.upc.edu",
                "displayName": "Max UPC",
                "permissions": [
                  "read",
                  "write",
                  "unsubscribe"
                ],

                // More properties here [..]

                "objectType": "subscription"
              }
            }

        The available actions are: subscribe, unsubscribe, change_permissions
        The username is the person who receives the action.
        The subscription object holds the subscription information of the
        username to the context
    """
    grok.context(ICommunity)
    grok.name('notify')

    @json_response
    def render(self):
        if self.request.method == 'POST':
            data = json.loads(self.request['BODY'])
            adapter = self.context.adapted()

            if 'read' in data['subscription']['permissions']:
                permission = u'reader'
            if 'write' in data['subscription']['permissions']:
                permission = u'writer'
            # For now, we took for granted that those users that has the
            # permissions 'flag', 'unsubscribe', 'invite' i 'kick' are owners
            if 'flag' in data['subscription']['permissions'] and \
               'unsubscribe' in data['subscription']['permissions'] and \
               'invite' in data['subscription']['permissions'] and \
               'kick' in data['subscription']['permissions']:
                permission = u'owner'

            if data['action'] == 'subscribe':
                adapter.update_acl_atomic(data['username'], permission)
            elif data['action'] == 'unsubscribe':
                adapter.remove_acl_atomic(data['username'])
            elif data['action'] == 'change_permissions':
                adapter.update_acl_atomic(data['username'], permission)

            acl = adapter.get_acl()

            # Finally, we update the plone permissions
            adapter.set_plone_permissions(acl)

            return dict(message='Done', status_code=200)

        if self.request.method != 'POST':
            return dict(error='Bad request. POST request expected.',
                        status_code=400)


class UploadFile(grok.View):
    grok.context(ICommunity)
    grok.name('upload')

    def canEditCommunity(self):
        return checkPermission('cmf.RequestReview', self.context)

    @memoize_contextless
    def portal_url(self):
        return self.portal().absolute_url()

    @memoize_contextless
    def portal(self):
        return getSite()

    def get_images_folder(self):
        """ Gets the media folder. It looks for it on the expected place with a
            fallback, just in case
        """
        if self.context.get('documents', False):
            if self.context['documents'].get('media', False):
                if IPhotosFolder.providedBy(self.context['documents']['media']):
                    return self.context['documents']['media']
        # Fallback
        for obj in self.context.objectIds():
            if IDocumentFolder.providedBy(self.context[obj]):
                for doc in self.context[obj].objectIds():
                    if IPhotosFolder.providedBy(self.context[obj][doc]):
                        return self.context[obj][doc]

    def get_documents_folder(self):
        """ Gets the documents folder. It looks for it on the expected place
            with a fallback, just in case
        """
        if self.context.get('documents', False):
            if IDocumentFolder.providedBy(self.context['documents']):
                return self.context['documents']
        # Fallback
        for obj in self.context.objectIds():
            if IDocumentFolder.providedBy(self.context[obj]):
                return self.context[obj]

    def render(self):
        if 'multipart/form-data' not in self.request['CONTENT_TYPE'] and \
           len(self.request.form.keys()) != 1:
            self.request.response.setHeader('Content-type', 'application/json')
            self.request.response.setStatus(400)
            return json.dumps({'Error': 'Not supported upload method'})

        for key in self.request.form.keys():
            if isinstance(self.request.form[key], FileUpload):
                file_key = key

        input_file = self.request.form[file_key]
        filename = input_file.filename
        activity_text = self.request.get('activity', '')

        ctr = api.portal.get_tool(name='content_type_registry')
        type_ = ctr.findTypeName(filename.lower(), '', '') or 'File'
        if type_ == 'File':
            container = self.get_documents_folder()
        else:
            container = self.get_images_folder()

        content_type = mimetypes.guess_type(filename)[0] or ''
        factory = IDXFileFactory(container)

        try:
            thefile = factory(filename, content_type, input_file, activity_text, self.request)
            self.request.response.setStatus(201)
            return json.dumps({'uploadURL': thefile.absolute_url(), 'thumbURL': '{}/@@images/image/mini'.format(thefile.absolute_url())})
        except Unauthorized:
            self.request.response.setHeader('Content-type', 'application/json')
            self.request.response.setStatus(401)
            return json.dumps({'Error': 'Unauthorized'})


class ToggleFavorite(grok.View):
    grok.context(IDexterityContent)
    grok.name('toggle-favorite')

    @json_response
    def render(self):
        if self.request.method == 'POST':
            current_user = api.user.get_current()
            if current_user.id in IFavorite(self.context).get():
                IFavorite(self.context).remove(current_user)
                return dict(message='UnFavorited', status_code=200)
            else:
                IFavorite(self.context).add(current_user)
                return dict(message='Favorited', status_code=200)

        if self.request.method != 'POST':
            return dict(error='Bad request. POST request expected.',
                        status_code=400)


class ToggleNotNotifyPush(grok.View):
    grok.context(IDexterityContent)
    grok.name('toggle-notnotifypush')

    @json_response
    def render(self):
        if self.request.method == 'POST':
            community = self.context
            adapter = community.adapted()
            current_user = api.user.get_current().id
            if current_user in INotNotifyPush(self.context).get():
                INotNotifyPush(self.context).remove(current_user)
                adapter.subscribe_user_push(current_user)
                return dict(message='Active notify push', status_code=200)
            else:
                INotNotifyPush(self.context).add(current_user)
                adapter.unsubscribe_user_push(current_user)
                return dict(message='Desactive notify push', status_code=200)

        if self.request.method != 'POST':
            return dict(error='Bad request. POST request expected.',
                        status_code=400)


class ToggleNotNotifyMail(grok.View):
    grok.context(IDexterityContent)
    grok.name('toggle-notnotifymail')

    @json_response
    def render(self):
        if self.request.method == 'POST':
            current_user = api.user.get_current()
            user_id = current_user.id

            if self.context.mails_users_community_black_lists is None:
                self.context.mails_users_community_black_lists = {}
            elif not isinstance(self.context.mails_users_community_black_lists, dict):
                self.context.mails_users_community_black_lists = ast.literal_eval(self.context.mails_users_community_black_lists)

            if user_id in self.context.mails_users_community_black_lists:
                self.context.mails_users_community_black_lists.pop(user_id)
                self.context.reindexObject()
                return dict(message='Active notify push', status_code=200)
            else:
                mail = current_user.getProperty('email')
                if mail is not None and mail != '':
                    self.context.mails_users_community_black_lists.update({user_id: mail})
                    self.context.reindexObject()
                    return dict(message='Desactive notify push', status_code=200)
                else:
                    return dict(error='Bad request. User not have email.',
                                status_code=400)

        if self.request.method != 'POST':
            return dict(error='Bad request. POST request expected.',
                        status_code=400)


class Subscribe(grok.View):
    """" Subscribe a requester user to an open community """
    grok.context(ICommunity)
    grok.name('subscribe')

    @json_response
    def render(self):
        community = self.context
        current_user = api.user.get_current()

        if self.request.method == 'POST':
            adapter = community.adapted()
            adapter.subscribe_user(current_user.id)
            return dict(message='Successfully unsubscribed')
        else:
            return dict(message='Bad request. POST request expected.',
                        status_code=400)


class UnSubscribe(grok.View):
    """ Unsubscribe from an Open or Closed community. """

    grok.context(ICommunity)
    grok.name('unsubscribe')

    @json_response
    def render(self):
        current_user = api.user.get_current()

        if self.request.method == 'POST':
            adapter = self.context.adapted()
            adapter.unsubscribe_user(current_user.id)

            community = self.context
            adapter = community.adapted()
            if current_user in INotNotifyPush(self.context).get():
                INotNotifyPush(self.context).remove(current_user)
                adapter.subscribe_user_push(current_user)

            if self.context.mails_users_community_black_lists is None:
                self.context.mails_users_community_black_lists = {}
            elif not isinstance(self.context.mails_users_community_black_lists, dict):
                self.context.mails_users_community_black_lists = ast.literal_eval(self.context.mails_users_community_black_lists)

            if current_user.id in self.context.mails_users_community_black_lists:
                self.context.mails_users_community_black_lists.pop(current_user.id)

            return dict(message='Successfully unsubscribed')
        else:
            return dict(error='Bad request. POST request expected.',
                        status_code=400)


class communityAdder(form.SchemaForm):
    grok.name('addCommunity')
    grok.context(IPloneSiteRoot)
    grok.require('ulearn.addCommunity')

    schema = ICommunity
    ignoreContext = True

    def update(self):
        super(communityAdder, self).update()
        self.actions['save'].addClass('context')

    def updateWidgets(self):
        super(communityAdder, self).updateWidgets()
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        if ulearn_tool.url_terms == None or ulearn_tool.url_terms == '':
           self.widgets['terms'].mode = 'hidden'
           self.fields['terms'].mode = 'hidden'
        else:
           self.widgets['terms'].mode = 'input'
           self.fields['terms'].mode = 'input'

        self.widgets['mails_users_community_lists'].mode = 'hidden'
        self.fields['mails_users_community_lists'].mode = 'hidden'

        self.widgets['mails_users_community_black_lists'].mode = 'hidden'
        self.fields['mails_users_community_black_lists'].mode = 'hidden'

    @button.buttonAndHandler(_(u'Crea la comunitat'), name='save')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            if 'title' not in data:
                msgid = _(u'falta_titol', default=u'No es pot crear una comunitat sense titol')
            elif 'terms' not in data:
                msgid = _(u'falta_condicions', default=u"Es necessari acceptar les condicions d'us i privacitat per crear una comunitat.")
            else:
                msgid = _(u'error', default=u"Falta omplir algun camp obligatori.")
            translated = self.context.translate(msgid)
            messages = IStatusMessage(self.request)
            messages.addStatusMessage(translated, type='error')
            return self.request.response.redirect(self.context.absolute_url())

        nom = data['title']
        description = data['description']
        image = data['image']
        community_type = data['community_type']
        activity_view = data['activity_view']
        tab_view = data['tab_view']
        show_news = data['show_news']
        show_events = data['show_events']
        twitter_hashtag = data['twitter_hashtag']
        notify_activity_via_push = data['notify_activity_via_push']
        notify_activity_via_push_comments_too = data['notify_activity_via_push_comments_too']
        notify_activity_via_mail = data['notify_activity_via_mail']
        type_notify = data['type_notify']
        mails_users_community_lists = data['mails_users_community_lists']
        mails_users_community_black_lists = data['mails_users_community_black_lists']
        distribution_lists = data['distribution_lists']

        terms = data['terms']

        portal = api.portal.get()
        pc = api.portal.get_tool('portal_catalog')

        nom = safe_unicode(nom)
        chooser = INameChooser(self.context)
        id_normalized = chooser.chooseName(nom, self.context.aq_parent)

        result = pc.unrestrictedSearchResults(portal_type='ulearn.community', id=id_normalized)

        if result:
            msgid = _(u'comunitat_existeix', default=u'La comunitat ${comunitat} ja existeix, si us plau, escolliu un altre nom.', mapping={u'comunitat': nom})

            translated = self.context.translate(msgid)

            messages = IStatusMessage(self.request)
            messages.addStatusMessage(translated, type='info')

            self.request.response.redirect('{}/++add++ulearn.community'.format(portal.absolute_url()))
        else:
            new_comunitat_id = self.context.invokeFactory(
                'ulearn.community',
                id_normalized,
                title=nom,
                description=description,
                image=image,
                community_type=community_type,
                activity_view=activity_view,
                tab_view=tab_view,
                show_news=show_news,
                show_events=show_events,
                twitter_hashtag=twitter_hashtag,
                notify_activity_via_push=notify_activity_via_push,
                notify_activity_via_push_comments_too=notify_activity_via_push_comments_too,
                notify_activity_via_mail=notify_activity_via_mail,
                type_notify=type_notify,
                mails_users_community_lists=mails_users_community_lists,
                mails_users_community_black_lists=mails_users_community_black_lists,
                distribution_lists=distribution_lists,
                terms=terms,
                checkConstraints=False)

            new_comunitat = self.context[new_comunitat_id]
            # Redirect back to the front page with a status message
            msgid = _(u'comunitat_creada', default=u'La comunitat ${comunitat} ha estat creada.', mapping={u'comunitat': nom})

            translated = self.context.translate(msgid)

            messages = IStatusMessage(self.request)
            messages.addStatusMessage(translated, type='info')

            self.request.response.redirect(new_comunitat.absolute_url())

    def terms(self):
        return 'terms' in self.fields.keys()


class communityEdit(form.SchemaForm):
    grok.name('editCommunity')
    grok.context(ICommunity)
    grok.require('cmf.ModifyPortalContent')

    schema = ICommunity
    ignoreContext = True

    ctype_map = {u'Closed': 'closed', u'Open': 'open', u'Organizative': 'organizative'}
    cview_map = {u'Darreres activitats': 'darreres_activitats', u'Activitats mes valorades': 'activitats_mes_valorades', u'Activitats destacades': 'activitats_destacades'}

    def update(self):
        super(communityEdit, self).update()
        self.actions['save'].addClass('context')

    def updateWidgets(self):
        super(communityEdit, self).updateWidgets()

        self.widgets['title'].value = self.context.title
        self.widgets['description'].value = self.context.description
        self.widgets['community_type'].value = [self.ctype_map[self.context.community_type]]
        self.widgets['activity_view'].value = [self.cview_map[self.context.activity_view]]
        self.widgets['tab_view'].value = [self.cview_map[self.context.tab_view]]
        self.widgets['show_news'].value = self.context.show_news
        self.widgets['show_events'].value = self.context.show_events
        self.widgets['twitter_hashtag'].value = self.context.twitter_hashtag
        self.widgets['notify_activity_via_mail'].value = [self.cview_map[self.context.notify_activity_via_mail]]
        self.widgets['type_notify'].value = [self.cview_map[self.context.type_notify]]
        self.widgets['mails_users_community_lists'].value = [self.cview_map[self.context.mails_users_community_lists]]
        self.widgets['mails_users_community_black_lists'].value = [self.cview_map[self.context.mails_users_community_black_lists]]
        self.widgets['distribution_lists'].value = [self.cview_map[self.context.distribution_lists]]
        self.widgets['terms'].value = ['true']

        if self.context.notify_activity_via_push:
            self.widgets['notify_activity_via_push'].value = ['selected']
            # Bool widgets should call update() once modified
            self.widgets['notify_activity_via_push'].update()

        if self.context.notify_activity_via_push_comments_too:
            self.widgets['notify_activity_via_push_comments_too'].value = ['selected']
            # Bool widgets should call update() once modified
            self.widgets['notify_activity_via_push_comments_too'].update()

        converter = SelectWidgetConverter(self.fields['readers'].field, self.widgets['readers'])
        self.widgets['readers'].value = converter.toWidgetValue(self.context.readers)

        converter = SelectWidgetConverter(self.fields['subscribed'].field, self.widgets['subscribed'])
        self.widgets['subscribed'].value = converter.toWidgetValue(self.context.subscribed)

        converter = SelectWidgetConverter(self.fields['owners'].field, self.widgets['owners'])
        self.widgets['owners'].value = converter.toWidgetValue(self.context.owners)

    @button.buttonAndHandler(_(u'Edita la comunitat'), name='save')
    def handleApply(self, action):
        data, errors = self.extractData()
        if errors:
            self.status = self.formErrorsMessage
            return

        nom = data['title']
        description = data['description']
        readers = data['readers']
        subscribed = data['subscribed']
        owners = data['owners']
        image = data['image']
        community_type = data['community_type']
        activity_view = data['activity_view']
        tab_view = data['tab_view']
        show_news = data['show_news']
        show_events = data['show_events']
        twitter_hashtag = data['twitter_hashtag']
        notify_activity_via_push = data['notify_activity_via_push']
        notify_activity_via_push_comments_too = data['notify_activity_via_push_comments_too']
        notify_activity_via_mail = data['notify_activity_via_mail']
        type_notify = data['type_notify']
        mails_users_community_lists = data['mails_users_community_lists']
        mails_users_community_black_lists = data['mails_users_community_black_lists']
        distribution_lists = data['distribution_lists']

        portal = getSite()
        pc = api.portal.get_tool(name='portal_catalog')
        result = pc.unrestrictedSearchResults(portal_type='ulearn.community', Title=nom)

        if result and self.context.title != nom:
            msgid = _(u'comunitat_existeix', default=u'La comunitat ${comunitat} ja existeix, si us plau, escolliu un altre nom.', mapping={u'comunitat': nom})

            translated = self.context.translate(msgid)

            messages = IStatusMessage(self.request)
            messages.addStatusMessage(translated, type='info')

            self.request.response.redirect('{}/edit'.format(self.context.absolute_url()))

        else:
            # Set new values in community
            self.context.title = nom
            self.context.description = description
            self.context.readers = readers
            self.context.subscribed = subscribed
            self.context.owners = owners
            self.context.community_type = community_type
            self.context.activity_view = activity_view
            self.context.tab_view = tab_view
            self.context.show_news = show_news
            self.context.show_events = show_events
            self.context.twitter_hashtag = twitter_hashtag
            self.context.notify_activity_via_push = notify_activity_via_push
            self.context.notify_activity_via_push_comments_too = notify_activity_via_push_comments_too
            self.context.notify_activity_via_mail = notify_activity_via_mail
            self.context.type_notify = type_notify
            self.context.mails_users_community_lists = mails_users_community_lists
            self.context.mails_users_community_black_lists = mails_users_community_black_lists
            self.context.distribution_lists = distribution_lists
            self.context.terms = True

            if image:
                self.context.image = image

            self.context.reindexObject()

            notify(ObjectModifiedEvent(self.context))

            msgid = _(u'comunitat_modificada', default=u'La comunitat ${comunitat} ha estat modificada.', mapping={u'comunitat': nom})

            translated = self.context.translate(msgid)

            messages = IStatusMessage(self.request)
            messages.addStatusMessage(translated, type='info')

            self.request.response.redirect(self.context.absolute_url())


# @grok.implementer(ICommunityInitializeAdapter)
# @grok.adapter(ICommunity, Interface)
class CommunityInitializeAdapter(object):
    """ Default adapter for initialize community custom actions """
    implements(ICommunityInitializeAdapter)
    adapts(ICommunity, Interface)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, community):
        """ On creation we only initialize the community based on its type and all
            the Plone-based processes. On the MAX side, for convenience we create
            the context directly into the MAX server with only the creator as
            subscriber (and owner).
        """
        initial_acl = dict(users=[dict(id=unicode(community.Creator().encode('utf-8')), role='owner')])
        adapter = community.adapted()

        adapter.create_max_context()
        adapter.set_initial_max_metadata()
        adapter.set_initial_subscription(initial_acl)
        adapter.set_plone_permissions(initial_acl)

        # Disable Inheritance
        community.__ac_local_roles_block__ = True

        # Auto-favorite the creator user to this community
        IFavorite(community).add(community.Creator())

        if is_activate_owncloud(self.context):
            client = getUtility(IOwncloudClient)
            session = client.admin_connection()
            # Create structure folders community in domain
            domain = api.portal.get_registry_record('ulearn5.owncloud.controlpanel.IOCSettings.connector_domain')
            try:
                session.file_info(domain.lower() + community.id)
            except OCSResponseError:
                logger.warning('The community {} not has been created in owncloud due to {}'.format(community.id, OCSResponseError))
                raise
            except HTTPResponseError as err:
                if err.status_code == 404:
                    session.mkdir(domain.lower() + '/' + community.id)

                    # Assign owner permissions
                    current = api.user.get_current()
                    session.share_file_with_user(domain.lower() + '/' + community.id, current.id, perms=Client.OCS_PERMISSION_ALL)  # Propietari
                else:
                    logger.warning('The community {} not has been created in owncloud due to {}'.format(community.id, err.status_code))
                    raise

        # Create default content containers
        documents = createContentInContainer(community, 'Folder', title='documents', checkConstraints=False)
        media = createContentInContainer(documents, 'Folder', title='media', checkConstraints=False)
        events = createContentInContainer(community, 'Folder', title='events', checkConstraints=False)
        news = createContentInContainer(community, 'Folder', title='news', checkConstraints=False)

        # Set the correct title, translated
        documents.setTitle(community.translate(_(u'Documents')))
        media.setTitle(community.translate(_(u'Media')))
        events.setTitle(community.translate(_(u'Esdeveniments')))
        news.setTitle(community.translate(_(u'Noticies')))

        # Set default view layout
        documents.setLayout('filtered_contents_search_view')
        media.setLayout('summary_view')
        events.setLayout('grid_events_view')
        news.setLayout('summary_view')

        # Mark them with a marker interface
        alsoProvides(documents, IDocumentFolder)
        alsoProvides(media, IPhotosFolder)
        alsoProvides(events, IEventsFolder)
        alsoProvides(news, INewsItemFolder)

        # Set on them the allowable content types
        behavior = ISelectableConstrainTypes(documents)
        behavior.setConstrainTypesMode(1)

        if is_activate_owncloud(self.context) and is_activate_externalstorage(self.context):
            behavior.setLocallyAllowedTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'CloudFile', 'ExternalContent'))
            behavior.setImmediatelyAddableTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'CloudFile', 'ExternalContent'))
        elif is_activate_etherpad(self.context) and is_activate_externalstorage(self.context):
            behavior.setLocallyAllowedTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'Etherpad', 'ExternalContent'))
            behavior.setImmediatelyAddableTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'Etherpad', 'ExternalContent'))
        elif is_activate_owncloud(self.context):
            behavior.setLocallyAllowedTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'CloudFile'))
            behavior.setImmediatelyAddableTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'CloudFile'))
        elif is_activate_externalstorage(self.context):
            behavior.setLocallyAllowedTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'ExternalContent'))
            behavior.setImmediatelyAddableTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'ExternalContent'))
        elif is_activate_etherpad(self.context):
            behavior.setLocallyAllowedTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'Etherpad'))
            behavior.setImmediatelyAddableTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder', 'Etherpad'))
        else:
            behavior.setLocallyAllowedTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder'))
            behavior.setImmediatelyAddableTypes(('Document', 'File', 'Folder', 'Link', 'Image', 'privateFolder'))

        behavior = ISelectableConstrainTypes(media)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Image', 'Folder'))
        behavior.setImmediatelyAddableTypes(('Image', 'Folder'))
        behavior = ISelectableConstrainTypes(events)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('Event', 'Folder', 'Image'))
        behavior.setImmediatelyAddableTypes(('Event', 'Folder', 'Image'))
        behavior = ISelectableConstrainTypes(news)
        behavior.setConstrainTypesMode(1)
        behavior.setLocallyAllowedTypes(('News Item', 'Folder', 'Image'))
        behavior.setImmediatelyAddableTypes(('News Item', 'Folder', 'Image'))

        NEWS_QUERY = [
            {'i': u'portal_type',
             'o': u'plone.app.querystring.operation.selection.any',
             'v': [u'News Item'],
             },
            {'i': u'review_state',
             'o': u'plone.app.querystring.operation.selection.any',
             'v': [u'published', u'intranet', u'esborrany'],
             },
            {'i': u'path',
             'o': u'plone.app.querystring.operation.string.relativePath',
             'v': u'..',
             },
        ]
        # 'v': u'..'}]
        QUERY_SORT_ON = u'effective'

        # Create the aggregator with new criteria
        col_news = createContentInContainer(news, 'Collection', title='aggregator', checkConstraints=False)
        col_news.setTitle(news.translate(_(u'Blog')))
        col_news.setDescription(news.translate(_(u'Noticies de la comunitat')))
        col_news.query = NEWS_QUERY
        col_news.sort_on = QUERY_SORT_ON
        col_news.sort_reversed = True
        col_news.item_count = 10
        news.setDefaultPage('aggregator')

        # Set default view from aggregator
        news['aggregator'].setLayout('collection_news_view')

        documents._Delete_objects_Permission = ('Site Administrator','Manager',)
        documents._Modify_portal_content_Permission = ('Site Administrator','Manager', 'WebMaster', 'Owner')
        events._Delete_objects_Permission = ('Site Administrator','Manager',)
        events._Modify_portal_content_Permission = ('Site Administrator','Manager', 'WebMaster', 'Owner')
        news._Delete_objects_Permission = ('Site Administrator','Manager',)
        news._Modify_portal_content_Permission = ('Site Administrator','Manager', 'WebMaster', 'Owner')
        col_news._Delete_objects_Permission = ('Site Administrator','Manager',)
        col_news._Modify_portal_content_Permission = ('Site Administrator','Manager', 'WebMaster', 'Owner')

        community._Delete_objects_Permission = ('Site Administrator','Manager', 'WebMaster', 'Owner')
        community._Modify_portal_content_Permission = ('Site Administrator','Manager', 'WebMaster', 'Owner')

        # Reindex all created objects
        community.reindexObject()
        documents.reindexObject()
        media.reindexObject()
        events.reindexObject()
        news.reindexObject()
        col_news.reindexObject()

        # Mark community as initialitzated, to avoid previous
        # folder creations to trigger modify event
        alsoProvides(community, IInitializedCommunity)


@grok.subscribe(ICommunity, IObjectAddedEvent)
def initialize_community(community, event):
    """ On creation we only initialize the community based on its type and all
        the Plone-based processes. On the MAX side, for convenience we create
        the context directly into the MAX server with only the creator as
        subscriber (and owner).
    """
    adapter = getMultiAdapter((event.object, event.object.REQUEST), ICommunityInitializeAdapter, name="init_community")
    adapter(community)


@grok.subscribe(ICommunity, IObjectModifiedEvent)
def edit_community(community, event):
    # Skip community modification if community is in creation state
    if not IInitializedCommunity.providedBy(community):
        return
    adapter = community.adapted()
    adapter.update_max_context()
    if ((community.notify_activity_via_mail == True) and (community.type_notify == 'Automatic')):
        acl = adapter.get_acl()
        adapter.update_mails_users(community, acl)

@grok.subscribe(ICommunity, IObjectRemovedEvent)
def delete_community(community, event):
    try:
        adapter = community.adapted()
        adapter.delete_community_all()
        portal = api.portal.get()
        if is_activate_owncloud(portal):
            portal_state = community.unrestrictedTraverse('@@plone_portal_state')
            root = getNavigationRootObject(community, portal_state.portal())
            ppath = community.getPhysicalPath()
            relative = ppath[len(root.getPhysicalPath()):]
            path = "/".join(relative)
            client = getUtility(IOwncloudClient)
            session = client.admin_connection()
            try:
                domain = get_domain()
                session.file_info(domain + '/' + path)
                session.delete(domain + '/' + path)
            except OCSResponseError:
                pass
            except HTTPResponseError as err:
                if err.status_code == 404:
                    logger.warning('The object {} has not been removed in owncloud'.format(path))

    except:
        logger.error('There was an error deleting the community {}'.format(community.absolute_url()))


# UTILITIES

@implementer(ICatalogFactory)
class ACLSoupCatalog(object):
    def __call__(self, context):
        catalog = Catalog()
        pathindexer = NodeAttributeIndexer('path')
        catalog['path'] = CatalogFieldIndex(pathindexer)
        hashindex = NodeAttributeIndexer('hash')
        catalog['hash'] = CatalogFieldIndex(hashindex)
        gwuuid = NodeAttributeIndexer('gwuuid')
        catalog['gwuuid'] = CatalogFieldIndex(gwuuid)
        groups = NodeAttributeIndexer('groups')
        catalog['groups'] = CatalogKeywordIndex(groups)
        return catalog


grok.global_utility(ACLSoupCatalog, name='communities_acl')


@implementer(ICatalogFactory)
class UserCommunityAccessCatalogFactory(object):
    """ Save the date of user access to the community
        :index user_community: TextIndex - user_community = current_user + '_' + community
        :index data_access: FieldIndex -  DateTime of user access to the community
    """

    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('user_community')
        catalog['user_community'] = CatalogTextIndex(idindexer)
        dataindexer = NodeAttributeIndexer('data_access')
        catalog['data_access'] = CatalogFieldIndex(dataindexer)
        return catalog


grok.global_utility(UserCommunityAccessCatalogFactory, name="user_community_access")

# INDEXERS TO CATALOG


@indexer(ICommunity)
def imageFilename(context):
    """ Create a catalogue indexer, registered as an adapter, which can
        populate the ``context.filename`` value and index it.
    """
    return context.image.filename


grok.global_adapter(imageFilename, name='image_filename')


@indexer(ICommunity)
def subscribed_items(context):
    """ Create a catalogue indexer, registered as an adapter, which can
        populate the ``context.subscribed`` value count it and index.
    """
    return len(list(set(context.readers + context.subscribed + context.owners)))


grok.global_adapter(subscribed_items, name='subscribed_items')


@indexer(ICommunity)
def subscribed_users(context):
    """ Create a catalogue indexer, registered as an adapter, which can
        populate the ``context.subscribed`` value count it and index.
    """
    return list(set(context.readers + context.subscribed + context.owners))


grok.global_adapter(subscribed_users, name='subscribed_users')


@indexer(ICommunity)
def community_type(context):
    """ Create a catalogue indexer, registered as an adapter, which can
        populate the ``community_type`` value count it and index.
    """
    return context.community_type


grok.global_adapter(community_type, name='community_type')


@indexer(ICommunity)
def community_hash(context):
    """ Create a catalogue indexer, registered as an adapter, which can
        populate the ``community_hash`` value count it and index.
    """
    registry = queryUtility(IRegistry)
    ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
    if ulearn_tool.url_site == None or ulearn_tool.url_site == '':
        return sha1(context.absolute_url()).hexdigest()
    else:
        return sha1(ulearn_tool.url_site + '/' + context.id).hexdigest()


grok.global_adapter(community_hash, name='community_hash')



@indexer(ICommunity)
def tab_view(context):
    """ Create a catalogue indexer, registered as an adapter, which can
        populate the ``community_type`` value count it and index.
    """
    return context.tab_view

grok.global_adapter(tab_view, name='tab_view')
