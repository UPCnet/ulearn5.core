# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from DateTime.DateTime import DateTime
from Products.CMFPlone.interfaces import IPloneSiteRoot
from StringIO import StringIO

from five import grok
from hashlib import sha1
from plone import api
from repoze.catalog.query import Eq
from souper.interfaces import ICatalogFactory
from souper.soup import Record
from souper.soup import get_soup
from zExceptions import Forbidden
from zope.component import getUtilitiesFor
from zope.component import getUtility

from base5.core.patches import changeMemberPortrait
from base5.core.utils import add_user_to_catalog
from base5.core.utils import get_all_user_properties
from base5.core.utils import remove_user_from_catalog
from mrs5.max.utilities import IMAXClient
from ulearn5.core.api import ApiResponse
from ulearn5.core.api import ObjectNotFound
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from ulearn5.core.browser.security import execute_under_special_role
from ulearn5.core.gwuuid import IGWUUID

from zope.component import getMultiAdapter
from itertools import chain

import ast
import json
import logging
import requests

logger = logging.getLogger(__name__)


class People(REST):
    """
        /api/people
        Returns all Users with their properties
    """

    placeholder_type = 'person'
    placeholder_id = 'username'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required=[])
    def GET(self):
        portal = api.portal.get()
        soup = get_soup('user_properties', portal)
        records = [r for r in soup.data.items()]

        result = {}
        user_properties_utility = getUtility(ICatalogFactory, name='user_properties')
        extender_name = api.portal.get_registry_record(
            'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
        for record in records:
            username = record[1].attrs['username']
            user = api.user.get(username=username)
            if user:
                rendered_properties = []
                if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
                    extended_user_properties_utility = getUtility(
                        ICatalogFactory, name=extender_name)
                    hasPublicProp = hasattr(
                        extended_user_properties_utility, 'public_properties')
                    for prop in extended_user_properties_utility.directory_properties:
                        if not hasPublicProp or (
                                hasPublicProp
                                and prop
                                in extended_user_properties_utility.public_properties):
                            userProp = user.getProperty(prop, '')
                            if userProp:
                                check = user.getProperty('check_' + prop, '')
                                if check == '' or check:
                                    rendered_properties.append(dict(
                                        name=prop,
                                        value=userProp,
                                        icon=extended_user_properties_utility.directory_icons[prop]
                                    ))
                else:
                    # If it's not extended, then return the simple set of data we know
                    # about the user using also the directory_properties field
                    hasPublicProp = hasattr(
                        user_properties_utility, 'public_properties')
                    for prop in user_properties_utility.directory_properties:
                        try:
                            if not hasPublicProp or (
                                    hasPublicProp
                                    and prop in user_properties_utility.public_properties):
                                userProp = user.getProperty(prop, '')
                                if userProp:
                                    check = user.getProperty('check_' + prop, '')
                                    if check == '' or check:
                                        rendered_properties.append(dict(
                                            name=prop,
                                            value=userProp,
                                            icon=user_properties_utility.directory_icons[prop],
                                        ))
                        except:
                            # Some users has @ in the username and is not valid...
                            pass

            result[record[1].attrs['id']] = rendered_properties

        return ApiResponse(result)


class Users(REST):
    """
        /api/people/users
    """
    grok.adapts(People, IPloneSiteRoot)
    grok.require('base.authenticated')

    def __init__(self, context, request):
        super(Users, self).__init__(context, request)

    @api_resource(required=[])
    def GET(self):
        portal = api.portal.get()
        soup = get_soup('user_properties', portal)
        records = [r for r in soup.data.items()]

        result = []
        for record in records:
            result.append(record[1].attrs['id'])

        result.sort()
        return ApiResponse(result)


class Sync(REST):
    """
        /api/people/sync
    """
    grok.adapts(People, IPloneSiteRoot)
    grok.require('base.authenticated')

    def __init__(self, context, request):
        super(Sync, self).__init__(context, request)

    @api_resource(required=['users'])
    def POST(self):
        """
            Syncs user local registry with remote ldap attributes
        """
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)
        users = self.params['users']

        notfound_errors = []
        properties_errors = []
        max_errors = []
        users_sync = []

        for userid in users:
            username = userid.lower()
            logger.info(
                '- API REQUEST /api/people/sync: Synchronize user {}'.format(username))
            user_memberdata = api.user.get(username=username)
            try:
                plone_user = user_memberdata.getUser()
            except:
                logger.info(
                    '- API REQUEST /api/people/sync: ERROR sync user {}'.format(username))
                notfound_errors.append(username)
                continue

            # Delete user cache
            for prop in plone_user.getOrderedPropertySheets():
                try:
                    ldap = prop
                    ldap._invalidateCache(plone_user)
                    plone_user._getPAS().ZCacheable_invalidate(view_name='_findUser-' + username)
                    ldap._getLDAPUserFolder(plone_user)._expireUser(plone_user)
                    break
                except:
                    continue

            response = {}
            try:
                user_memberdata = api.user.get(username=username)
                plone_user = user_memberdata.getUser()
            except:
                notfound_errors.append(username)
                logger.error(
                    'User {} cannot be found in LDAP repository'.format(username))
            else:
                try:
                    properties = get_all_user_properties(plone_user)
                    add_user_to_catalog(plone_user, properties, overwrite=True)
                except:
                    logger.error(
                        'Cannot update properties catalog for user {}'.format(username))
                    properties_errors.append(username)

                try:
                    fullname = properties.get('fullname', '')
                    maxclient.people.post(username=username, displayName=fullname)

                    # If user hasn't been created right now, update displayName
                    if maxclient.last_response_code == 200:
                        maxclient.people[username].put(displayName=fullname)
                    users_sync.append(username)
                    logger.info(
                        '- API REQUEST /api/people/sync: OK sync user {}'.format(username))
                except:
                    logger.error(
                        'User {} couldn\'t be created or updated on max'.format(
                            username))
                    max_errors.append(username)

        response = {}
        if notfound_errors:
            response['not_found'] = notfound_errors
        if properties_errors:
            response['properties_errors'] = properties_errors
        if max_errors:
            response['max_errors'] = max_errors
        response['synced_users'] = users_sync

        return ApiResponse(response)


class Person(REST):
    """
        /api/people/{username}
    """

    grok.adapts(People, IPloneSiteRoot)
    grok.require('base.authenticated')

    def __init__(self, context, request):
        super(Person, self).__init__(context, request)

    @api_resource(required=['username', 'fullname', 'email', 'password'])
    def POST(self):
        """
            Creates a user
        """
        userid = self.params.pop('username')
        username = userid.lower()
        email = self.params.pop('email')
        password = self.params.pop('password', None)

        response = self.create_user(
            username,
            email,
            password,
            **self.params
        )

        return response

    @api_resource()
    def DELETE(self):
        """
            Deletes a user from the plone & max & communities subscribe
        """
        self.deleteMembers([self.params['username']])
        remove_user_from_catalog(self.params['username'].lower())
        pc = api.portal.get_tool(name='portal_catalog')
        username = self.params['username']

        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        # portal_url = api.portal.get().absolute_url()
        communities_subscription = maxclient.people[username].subscriptions.get()

        if communities_subscription != []:

            for num, community_subscription in enumerate(communities_subscription):
                community = pc.unrestrictedSearchResults(
                    portal_type="ulearn.community",
                    community_hash=community_subscription['hash'])
                try:
                    obj = community[0]._unrestrictedGetObject()
                    logger.info('Processant {} de {}. Comunitat {}'.format(
                        num, len(communities_subscription), obj))
                    gwuuid = IGWUUID(obj).get()
                    portal = api.portal.get()
                    soup = get_soup('communities_acl', portal)

                    records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

                    # Save ACL into the communities_acl soup
                    if records:
                        acl_record = records[0]
                        acl = acl_record.attrs['acl']
                        exist = [a for a in acl['users']
                                 if a['id'] == unicode(username)]
                        if exist:
                            acl['users'].remove(exist[0])
                            acl_record.attrs['acl'] = acl
                            soup.reindex(records=[acl_record])
                            adapter = obj.adapted()
                            adapter.set_plone_permissions(adapter.get_acl())

                except:
                    continue

        maxclient.people[username].delete()
        logger.info('Delete user: {}'.format(username))
        return ApiResponse({}, code=204)

    def create_user(self, username, email, password, **properties):
        existing_user = api.user.get(username=username)
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        avatar = properties.pop('avatar', None)

        if not existing_user:
            args = dict(
                email=email,
                username=username,
                properties=properties
            )
            if password:
                args['password'] = password
            api.user.create(**args)
            maxclient.people[username].put(displayName=properties['fullname'])
            # Save the image into the Plone user profile if provided
            if avatar:
                portal = api.portal.get()
                membership_tool = api.portal.get_tool(name='portal_membership')
                imgName = (avatar.split('/')[-1]).decode('utf-8')
                imgData = requests.get(avatar).content
                image = StringIO(imgData)
                image.filename = imgName
                execute_under_special_role(portal,
                                           "Manager",
                                           changeMemberPortrait,
                                           membership_tool,
                                           image,
                                           username)

            status = 201

        else:
            # Update portal membership user properties
            properties.update({'email': email})
            existing_user.setMemberProperties(properties)

            # Update MAX properties
            # Just to make sure user exists (in case it was only on ldap)
            maxclient.people[username].post()
            status = maxclient.last_response_code
            maxclient.people[username].put(displayName=properties['fullname'])

            if avatar:
                portal = api.portal.get()
                membership_tool = api.portal.get_tool(name='portal_membership')
                imgName = (avatar.split('/')[-1]).decode('utf-8')
                imgData = requests.get(avatar).content
                image = StringIO(imgData)
                image.filename = imgName
                execute_under_special_role(portal,
                                           "Manager",
                                           changeMemberPortrait,
                                           membership_tool,
                                           image,
                                           username)

        if status == 201:
            return ApiResponse.from_string(
                'User {} created'.format(username),
                code=status)
        else:
            return ApiResponse.from_string('User {} updated'.format(username), code=200)

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

        # Delete member data in portal_memberdata.
        mdtool = api.portal.get_tool(name='portal_memberdata')
        if mdtool is not None:
            for member_id in member_ids:
                mdtool.deleteMemberData(member_id)

                # Guardamos el username en el soup para borrar el usuario del local roles
                portal = api.portal.get()
                soup_users_delete = get_soup('users_delete_local_roles', portal)
                exist = [r for r in soup_users_delete.query(
                    Eq('id_username', member_id))]

                if not exist:
                    record = Record()
                    record.attrs['id_username'] = member_id
                    soup_users_delete.add(record)
                    soup_users_delete.reindex()

        # OJO se quita porque si el site es muy grande al recorrer todo para borrar da Time-out y
        # ademas consume mucha memoria y tumba los zopes.
        # Hemos creado la vista delete_local_roles en base5.core.setup.py que ejecuta esto.

        # portal = getUtility(ISiteRoot)
        # reindex = 1
        # recursive = 1
        # # Delete members' local roles.
        # execute_under_special_role(portal,
        #                            "Manager",
        #                            mtool.deleteLocalRoles,
        #                            portal,
        #                            member_ids,
        #                            reindex,
        #                            recursive)

    @api_resource(required=['username'])
    def PUT(self):
        """
            Modify displayName user

            /api/people/{username}

            data = {'displayName':'Nom Cognom'}

        """
        existing_user = api.user.get(username=self.params['username'].lower())
        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        if existing_user:
            if 'displayName' in self.params:
                # Update portal membership user properties
                existing_user.setMemberProperties(
                    {'fullname': self.params['displayName']})
                properties = get_all_user_properties(existing_user)
                add_user_to_catalog(existing_user, properties, overwrite=True)
                username = self.params['username'].lower()
                # Update max
                maxclient.people[username].put(displayName=properties['fullname'])
                status = maxclient.last_response_code
            else:
                status = 500
        else:
            status = 404

        if status == 404:
            return ApiResponse.from_string(
                'User {} not found'.format(self.params['username'].lower()),
                code=status)
        elif status == 200:
            return ApiResponse.from_string(
                'User {} updated'.format(self.params['username'].lower()),
                code=status)
        elif status == 500:
            return ApiResponse.from_string(
                'User {} not updated. Not displayName.'.format(
                    self.params['username'].lower()),
                code=status)

    # @api_resource(required=['username', 'email'])
    # def PUT(self):
    #     """
    #         Modify email user
    #     """
    #     existing_user = api.user.get(username=self.params['username'].lower())
    #     if existing_user:
    #         # Update portal membership user properties
    #         existing_user.setMemberProperties({'email': self.params['email']})
    #         properties = get_all_user_properties(existing_user)
    #         add_user_to_catalog(existing_user, properties, overwrite=True)
    #         status = 200
    #     else:
    #         status = 404

    #     if status == 404:
    #         return ApiResponse.from_string('User {} not found'.format(self.params['username'].lower()), code=status)
    #     elif status == 200:
    #         return ApiResponse.from_string('User {} updated'.format(self.params['username'].lower()), code=status)

    @api_resource(required=['username'])
    def GET(self):
        """ Returns the user profile values. """
        username = self.params['username'].lower()
        user = api.user.get(username=username)
        if user:
            user_properties_utility = getUtility(
                ICatalogFactory, name='user_properties')

            rendered_properties = []
            try:
                extender_name = api.portal.get_registry_record(
                    'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
                if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
                    extended_user_properties_utility = getUtility(
                        ICatalogFactory, name=extender_name)
                    hasPublicProp = hasattr(
                        extended_user_properties_utility, 'public_properties')
                    for prop in extended_user_properties_utility.directory_properties:
                        if not hasPublicProp or (
                                hasPublicProp
                                and prop
                                in extended_user_properties_utility.public_properties):
                            userProp = user.getProperty(prop, '')
                            if userProp:
                                check = user.getProperty('check_' + prop, '')
                                if check == '' or check:
                                    rendered_properties.append(dict(
                                        name=prop,
                                        value=userProp,
                                        icon=extended_user_properties_utility.directory_icons[prop]
                                    ))
                else:
                    # If it's not extended, then return the simple set of data we know
                    # about the user using also the directory_properties field
                    hasPublicProp = hasattr(
                        user_properties_utility, 'public_properties')
                    for prop in user_properties_utility.directory_properties:
                        try:
                            if not hasPublicProp or (
                                    hasPublicProp
                                    and prop in user_properties_utility.public_properties):
                                userProp = user.getProperty(prop, '')
                                if userProp:
                                    check = user.getProperty('check_' + prop, '')
                                    if check == '' or check:
                                        rendered_properties.append(dict(
                                            name=prop,
                                            value=userProp,
                                            icon=user_properties_utility.directory_icons[prop],
                                        ))
                        except:
                            # Some users has @ in the username and is not valid...
                            pass
            except:
                raise ObjectNotFound('User not found')

            return ApiResponse(rendered_properties)
        else:
            raise ObjectNotFound('User not found')


class All(REST):
    """
        /api/people/{username}/all

        Returns the user all properties values.
    """

    grok.adapts(Person, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required=['username'])
    def GET(self):
        """ Returns the user all profile values. """
        username = self.params['username'].lower()
        user = api.user.get(username=username)
        if user:
            userid = user.id.lower()
            user_properties_utility = getUtility(
                ICatalogFactory, name='user_properties')
            rendered_properties = {userid: {}}
            try:
                extender_name = api.portal.get_registry_record(
                    'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
                if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
                    extended_user_properties_utility = getUtility(
                        ICatalogFactory, name=extender_name)
                    for prop in extended_user_properties_utility.properties:
                        userProp = user.getProperty(prop, '')
                        if userProp:
                            rendered_properties[userid].update({prop: userProp})
                else:
                    for prop in user_properties_utility.properties:
                        userProp = user.getProperty(prop, '')
                        if userProp:
                            rendered_properties[userid].update({prop: userProp})
            except:
                raise ObjectNotFound('User not found')

            return ApiResponse(rendered_properties)
        else:
            raise ObjectNotFound('User not found')


class Ushare(REST):
    """
        /api/people/{username}/ushare

        Returns the user properties values for ushare.

        :param domain
    """

    grok.adapts(Person, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required=['username'])
    def GET(self):
        """ Returns the user all profile values. """
        username = self.params['username'].lower()
        user = api.user.get(username=username)
        if user:
            ts = api.portal.get_tool(name='translation_service')
            domain = self.params.pop('domain', None)
            domain = 'ulearn5.' + domain if domain else 'ulearn'

            current = api.user.get_current()
            lang = current.getProperty('language')

            user_properties_utility = getUtility(
                ICatalogFactory, name='user_properties')

            rendered_properties = []
            try:
                extender_name = api.portal.get_registry_record(
                    'base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender')
                if extender_name in [a[0] for a in getUtilitiesFor(ICatalogFactory)]:
                    user_properties_utility = getUtility(
                        ICatalogFactory, name=extender_name)

                hasPublicProp = hasattr(user_properties_utility, 'public_properties')
                for prop in user_properties_utility.directory_properties:
                    try:
                        if prop not in ['fullname', 'email']:
                            if not hasPublicProp or (
                                    hasPublicProp
                                    and prop in user_properties_utility.public_properties):
                                userProp = user.getProperty(prop, '')
                                if userProp:
                                    check = user.getProperty('check_' + prop, '')
                                    if check == '' or check:
                                        rendered_properties.append(
                                            dict(
                                                key=prop, name=ts.translate(
                                                    prop, context=self.request,
                                                    domain=domain, target_language=lang),
                                                value=userProp,))
                    except:
                        # Some users has @ in the username and is not valid...
                        pass

                result = {
                    'username':  user.id,
                    'fullname': user.getProperty('fullname', ''),
                    'email': user.getProperty('email', ''),
                    'language': user.getProperty('language', 'ca'),
                    'more_info': rendered_properties
                }

            except:
                raise ObjectNotFound('User not found')

            return ApiResponse(result)
        else:
            raise ObjectNotFound('User not found')


class Subscriptions(REST):
    """
        /api/people/{username}/subscriptions

        Manages the user subscriptions.
    """

    grok.adapts(Person, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource()
    def GET(self):
        """ Returns all the user communities."""
        # Hard security validation as the view is soft checked
        check_permission = self.check_roles(roles=['Member', ])
        if check_permission is not True:
            return check_permission

        # Get all communities for the current user
        pc = api.portal.get_tool('portal_catalog')
        r_results_organizative = pc.searchResults(
            portal_type="ulearn.community", community_type=u"Organizative",
            sort_on="sortable_title")
        r_results_closed = pc.searchResults(
            portal_type="ulearn.community", community_type=u"Closed",
            sort_on="sortable_title")
        ur_results_open = pc.unrestrictedSearchResults(
            portal_type="ulearn.community", community_type=u"Open",
            sort_on="sortable_title")
        communities = r_results_organizative + r_results_closed + ur_results_open

        self.is_role_manager = False
        self.username = api.user.get_current().id
        global_roles = api.user.get_roles()
        if 'Manager' in global_roles:
            self.is_role_manager = True

        portal_url = api.portal.get().absolute_url()

        maxclient, settings = getUtility(IMAXClient)()
        maxclient.setActor(settings.max_restricted_username)
        maxclient.setToken(settings.max_restricted_token)

        communities_subscription = maxclient.people[self.username].subscriptions.get()

        result = []
        favorites = self.get_favorites()
        notnotifypush = self.get_notnotifypush()
        for obj in communities_subscription:
            brain = [i for i in communities if i.community_hash == obj['hash']]
            if brain:
                brain = brain[0]
                can_write = True if 'write' in obj['permissions'] else False
                brainObj = self.context.unrestrictedTraverse(brain.getPath())

                if brainObj.mails_users_community_black_lists is None:
                    brainObj.mails_users_community_black_lists = {}
                elif not isinstance(brainObj.mails_users_community_black_lists, dict):
                    brainObj.mails_users_community_black_lists = ast.literal_eval(
                        brainObj.mails_users_community_black_lists)

                community = dict(id=brain.id,
                                title=brain.Title,
                                description=brain.Description,
                                url=brain.getURL(),
                                gwuuid=brain.gwuuid,
                                hash=sha1(brain.getURL()).hexdigest(),
                                type=brain.community_type,
                                image=brain.image_filename if brain.image_filename else False,
                                image_url=brain.getURL() + '/thumbnail-image' if brain.image_filename else portal_url + '/++theme++ulearn5/assets/images/avatar_default.png',
                                favorited=brain.id in favorites,
                                pending=self.get_pending_community_user(brain, self.username),
                                activate_notify_push=brainObj.notify_activity_via_push or brainObj.notify_activity_via_push_comments_too,
                                activate_notify_mail=brainObj.notify_activity_via_mail and brainObj.type_notify == 'Automatic',
                                not_notify_push=brain.id in notnotifypush,
                                not_notify_mail=self.username in brainObj.mails_users_community_black_lists,
                                can_manage=self.is_community_manager(brain),
                                can_write=can_write)
                result.append(community)

        return ApiResponse(result)

    def get_favorites(self):
        pc = api.portal.get_tool('portal_catalog')

        results = pc.unrestrictedSearchResults(favoritedBy=self.username)
        return [favorites.id for favorites in results]

    def get_notnotifypush(self):
        pc = api.portal.get_tool('portal_catalog')

        results = pc.unrestrictedSearchResults(notNotifyPushBy=self.username)
        return [notnotifypush.id for notnotifypush in results]

    def is_community_manager(self, community):
        # The user has role Manager
        if self.is_role_manager:
            return True

        gwuuid = community.gwuuid
        portal = api.portal.get()
        soup = get_soup('communities_acl', portal)

        records = [r for r in soup.query(Eq('gwuuid', gwuuid))]
        if records:
            return self.username in [
                a['id'] for a in records[0].attrs['acl']['users']
                if a['role'] == u'owner']

    @staticmethod
    def get_pending_community_user(community, user):
        """ Returns the number of pending objects to see in the community. """
        def get_data_acces_community_user():
            """ Returns the date of user access to the community. """
            user_community = user + '_' + community.id
            portal = api.portal.get()

            soup_access = get_soup('user_community_access', portal)
            exist = [r for r in soup_access.query(Eq('user_community', user_community))]
            if not exist:
                return DateTime()
            else:
                return exist[0].attrs['data_access']

        # Suma 0.001 para que no muestre los que acaba de crear el usuario
        data_access = get_data_acces_community_user() + 0.001
        now = DateTime() + 0.001  # Suma 0.001 para que no muestre los que acaba de crear el usuario
        pc = api.portal.get_tool(name="portal_catalog")

        date_range_query = {'query': (data_access, now), 'range': 'min:max'}

        results = pc.searchResults(path=community.getPath(),
                                   created=date_range_query)
        valor = len(results)
        if valor > 0:
            return valor
        else:
            return 0


class Visualizations(REST):
    """
        /api/people/{username}/visualizations

        Quan accedeixes a la comunitat, actualitza la data d'accés de l'usuari
        i per tant, el comptador de visualitzacions pendents queda a 0.
    """
    grok.adapts(Person, IPloneSiteRoot)

    @api_resource(required=['username'])
    def PUT(self):
        """ Update pending visualitzations. """
        body = self.request.get('BODY', False)
        if not body:
            return self.error("Bad Request", "Body are required.", 400)

        data = json.loads(body)
        community = data.get('community', False)
        if not community:
            return self.error("Bad Request", "Community id in body are required.", 400)

        portal = api.portal.get()
        current_user = self.params['username'].lower()
        user_community = current_user + '_' + community
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

        return ApiResponse({"success": "Visualitzacions pendents actualitzades."})

class UsersPropertiesMigration(REST):
    """
        /api/userspropertiesmigration
    """

    placeholder_type = 'person'
    placeholder_id = 'username'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    def GET(self):
        """ Returns all users properties """

        # Get all ldap users
        searchString = ''
        searchView = getMultiAdapter((aq_inner(self.context), self.request), name='pas_search')
        ldap_users = searchView.merge(chain(*[searchView.searchUsers(**{field: searchString}) for field in ['name']]), 'userid')

        result = []
        for user in ldap_users:
            user = api.user.get(username=user['id'])
            properties = get_all_user_properties(user)

            try:
                info_user = dict(id=user.id,
                                 properties=properties
                                 )
                result.append(info_user)
            except:
                logger.info('HA FALLAT LA INFO DE {}'.format(user.id))

        return json.dumps(result)


class UsersPropertiesMigrationSoup(REST):
    """
        /api/userspropertiesmigrationsoup
    """

    placeholder_type = 'person'
    placeholder_id = 'username'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    def GET(self):
        """ Returns all users properties """

        # Get all users soup
        portal = api.portal.get()
        soup = get_soup('user_properties', portal)
        records = [r for r in soup.data.items()]
        result = []
        for record in records:
            userid = str(record[1].attrs['id'])
            user = api.user.get(username=userid)
            try:
                properties = get_all_user_properties(user)
            except:
                pass

            try:
                info_user = dict(id=user.id,
                                 properties=properties
                                 )
                result.append(info_user)
            except:
                logger.info('HA FALLAT LA INFO DE {}'.format(userid))

        return json.dumps(result)