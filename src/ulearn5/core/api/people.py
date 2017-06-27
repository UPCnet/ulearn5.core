# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from five import grok
from zope.component import getUtility

from Products.CMFCore.utils import getToolByName
from Products.CMFPlone.interfaces import IPloneSiteRoot
from plone import api

from base5.core.patches import changeMemberPortrait
from mrs5.max.utilities import IMAXClient

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from ulearn5.core.browser.security import execute_under_special_role

from StringIO import StringIO
from base5.core.utils import add_user_to_catalog
from base5.core.utils import get_all_user_properties
from base5.core.utils import remove_user_from_catalog
from repoze.catalog.query import Eq
from souper.soup import get_soup
from ulearn5.core.gwuuid import IGWUUID
from ulearn5.core.content.community import ICommunityACL

import logging
import requests

from Products.CMFCore.interfaces import ISiteRoot

logger = logging.getLogger(__name__)


class People(REST):
    """
        /api/people
    """

    placeholder_type = 'person'
    placeholder_id = 'username'

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')


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

        for userid in users:
            username = userid.lower()
            user_memberdata = api.user.get(username=username)
            plone_user = user_memberdata.getUser()

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

            try:
                user_memberdata = api.user.get(username=username)
                plone_user = user_memberdata.getUser()
            except:
                notfound_errors.append(username)
                logger.error('User {} cannot be found in LDAP repository'.format(username))
            else:
                try:
                    properties = get_all_user_properties(plone_user)
                    add_user_to_catalog(plone_user, properties, overwrite=True)
                except:
                    logger.error('Cannot update properties catalog for user {}'.format(username))
                    properties_errors.append(username)

                try:
                    fullname = properties.get('fullname', '')
                    maxclient.people.post(username=username, displayName=fullname)

                    # If user hasn't been created right now, update displayName
                    if maxclient.last_response_code == 200:
                        maxclient.people[username].put(displayName=fullname)

                except:
                    logger.error('User {} couldn\'t be created or updated on max'.format(username))
                    max_errors.append(username)

        response = {}
        if notfound_errors:
            response['not_found'] = notfound_errors
        if properties_errors:
            response['properties_errors'] = properties_errors
        if max_errors:
            response['max_errors'] = max_errors

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

        portal_url = api.portal.get().absolute_url()
        communities_subscription = maxclient.people[username].subscriptions.get()

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
                        exist = [a for a in acl['users'] if a['id'] == unicode(username)]
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
                membership_tool = getToolByName(portal, 'portal_membership')
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
            has_email = existing_user.getProperty('email', False)
            if not has_email:
                properties.update({'email': email})

            existing_user.setMemberProperties(properties)

            # Update MAX properties
            maxclient.people[username].post()  # Just to make sure user exists (in case it was only on ldap)
            status = maxclient.last_response_code
            maxclient.people[username].put(displayName=properties['fullname'])

            if avatar:
                portal = api.portal.get()
                membership_tool = getToolByName(portal, 'portal_membership')
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
            return ApiResponse.from_string('User {} created'.format(username), code=status)
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

        portal = getUtility(ISiteRoot)
        reindex = 1
        recursive = 1
        # Delete members' local roles.
        execute_under_special_role(portal,
                                   "Manager",
                                   mtool.deleteLocalRoles,
                                   portal,
                                   member_ids,
                                   reindex,
                                   recursive)


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
        r_results = pc.searchResults(portal_type='ulearn.community', community_type=[u'Closed', u'Organizative'])
        ur_results = pc.unrestrictedSearchResults(portal_type='ulearn.community', community_type=u'Open')
        communities = r_results + ur_results

        self.is_role_manager = False
        self.username = api.user.get_current().id
        global_roles = api.user.get_roles()
        if 'Manager' in global_roles:
            self.is_role_manager = True

        result = []
        favorites = self.get_favorites()
        for brain in communities:
            community = dict(id=brain.id,
                             title=brain.Title,
                             description=brain.Description,
                             url=brain.getURL(),
                             gwuuid=brain.gwuuid,
                             type=brain.community_type,
                             image=brain.image_filename if brain.image_filename else False,
                             favorited=brain.id in favorites,
                             can_manage=self.is_community_manager(brain))
            result.append(community)

        return ApiResponse(result)

    def get_favorites(self):
        pc = api.portal.get_tool('portal_catalog')

        results = pc.unrestrictedSearchResults(favoritedBy=self.username)
        return [favorites.id for favorites in results]

    def is_community_manager(self, community):
        # The user has role Manager
        if self.is_role_manager:
            return True

        gwuuid = community.gwuuid
        portal = api.portal.get()
        soup = get_soup('communities_acl', portal)

        records = [r for r in soup.query(Eq('gwuuid', gwuuid))]
        if records:
            return self.username in [a['id'] for a in records[0].attrs['acl']['users'] if a['role'] == u'owner']
