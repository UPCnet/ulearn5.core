# -*- coding: utf-8 -*-
from hashlib import sha1
from plone import api
from AccessControl import Unauthorized
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.component import getAdapter

from plone.app.testing import login
from plone.app.testing import logout

from Products.CMFCore.utils import getToolByName

from repoze.catalog.query import Eq
from souper.soup import get_soup

from ulearn5.core.gwuuid import IGWUUID

from mrs5.max.utilities import IMAXClient
from ulearn5.core.tests import uLearnTestBase
from ulearn5.core.content.community import ICommunityTyped
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING

from ulearn5.core.content.community import OPEN_PERMISSIONS
from ulearn5.core.content.community import CLOSED_PERMISSIONS
from ulearn5.core.content.community import ORGANIZATIVE_PERMISSIONS
from ulearn5.core.tests.mockers import http_mock_hub_syncacl

import httpretty
import json


class TestExample(uLearnTestBase):

    layer = ULEARN5_CORE_INTEGRATION_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.qi_tool = getToolByName(self.portal, 'portal_quickinstaller')

        self.maxclient, self.settings = getUtility(IMAXClient)()
        self.username = self.settings.max_restricted_username
        self.token = self.settings.max_restricted_token

        self.maxclient.setActor(self.settings.max_restricted_username)
        self.maxclient.setToken(self.settings.max_restricted_token)

    def tearDown(self):
        httpretty.disable()
        httpretty.reset()

        self.maxclient.contexts['http://nohost/plone/community-test'].delete()
        self.maxclient.contexts['http://nohost/plone/community-test2'].delete()
        self.maxclient.contexts['http://nohost/plone/community-test-open'].delete()
        self.maxclient.contexts['http://nohost/plone/community-test-notify'].delete()

    def get_max_subscribed_users(self, community):
        return [user.get('username', '') for user in self.maxclient.contexts[community.absolute_url()].subscriptions.get(qs={'limit': 0})]

    def test_product_is_installed(self):
        """ Validate that our products GS profile has been run and the product
            installed
        """
        pid = 'ulearn5.core'
        installed = [p['id'] for p in self.qi_tool.listInstalledProducts()]
        self.assertTrue(pid in installed,
                        'package appears not to have been installed')

    def test_permissions_on_homepage_and_frontpage(self):
        self.assertTrue(self.portal['front-page'].get_local_roles()[0][0], 'AuthenticatedUsers')
        self.assertTrue(self.portal.get_local_roles()[0][0], 'AuthenticatedUsers')

    def test_community_creation_closed(self):
        nom = u'community-test'
        description = 'Blabla'
        image = None
        community_type = 'Closed'
        twitter_hashtag = 'helou'

        login(self.portal, 'ulearn.testuser1')

        self.portal.invokeFactory('ulearn.community', 'community-test',
                                 title=nom,
                                 description=description,
                                 image=image,
                                 community_type=community_type,
                                 twitter_hashtag=twitter_hashtag)

        community = self.portal['community-test']

        logout()

        # Test for the acl registry
        soup = get_soup('communities_acl', self.portal)
        # By the gwuuid
        records = [r for r in soup.query(Eq('gwuuid', IGWUUID(community).get()))]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].attrs.get('gwuuid', ''), IGWUUID(community).get())
        self.assertEqual(records[0].attrs.get('path', ''), '/'.join(community.getPhysicalPath()))
        self.assertEqual(records[0].attrs.get('hash', ''), sha1(community.absolute_url()).hexdigest())
        self.assertEqual(records[0].attrs.get('acl', '').get('users', [])[0]['role'], u'owner')
        self.assertEqual(records[0].attrs.get('acl', '').get('users', [])[0]['id'], u'ulearn.testuser1')

        # Test for internal objects
        self.assertEqual(community.objectIds(), ['documents', 'events', 'news'])

        # Test for photo folder
        self.assertEqual(community['documents'].objectIds(), ['media', ])

        # Test for subscribed users
        self.assertTrue(u'ulearn.testuser1' in self.get_max_subscribed_users(community))

        # Test for Plone permissions/local roles
        self.assertTrue('Reader' not in community.get_local_roles_for_userid(userid='AuthenticatedUsers'))
        self.assertTrue('Editor' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))
        self.assertTrue('Owner' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))
        self.assertTrue('Reader' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))

        # Test the initial MAX properties
        max_community_info = self.get_max_context_info(community)
        self.assertEqual('helou', max_community_info.get(u'twitterHashtag', ''))
        self.assertFalse(max_community_info.get(u'notifications', False))
        self.assertTrue(u'[COMMUNITY]' in max_community_info.get('tags', []))

        for key in CLOSED_PERMISSIONS:
            self.assertEqual(max_community_info['permissions'].get(key, ''), CLOSED_PERMISSIONS[key])

    def test_community_creation_open(self):
        nom = u'community-test'
        description = 'Blabla'
        image = None
        community_type = 'Open'
        twitter_hashtag = 'helou'

        login(self.portal, 'ulearn.testuser1')

        self.portal.invokeFactory('ulearn.community', 'community-test',
                                 title=nom,
                                 description=description,
                                 image=image,
                                 community_type=community_type,
                                 twitter_hashtag=twitter_hashtag)

        community = self.portal['community-test']

        logout()

        # Test for the acl registry
        soup = get_soup('communities_acl', self.portal)
        # By the gwuuid
        records = [r for r in soup.query(Eq('gwuuid', IGWUUID(community).get()))]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].attrs.get('gwuuid', ''), IGWUUID(community).get())
        self.assertEqual(records[0].attrs.get('path', ''), '/'.join(community.getPhysicalPath()))
        self.assertEqual(records[0].attrs.get('hash', ''), sha1(community.absolute_url()).hexdigest())
        self.assertEqual(records[0].attrs.get('acl', '').get('users', [])[0]['role'], u'owner')
        self.assertEqual(records[0].attrs.get('acl', '').get('users', [])[0]['id'], u'ulearn.testuser1')

        # Test for internal objects
        self.assertEqual(community.objectIds(), ['documents', 'events', 'news'])

        # Test for photo folder
        self.assertEqual(community['documents'].objectIds(), ['media', ])

        # Test for subscribed users
        self.assertTrue(u'ulearn.testuser1' in self.get_max_subscribed_users(community))

        # Test for Plone permissions/local roles
        self.assertTrue('Reader' not in community.get_local_roles_for_userid(userid='AuthenticatedUsers'))
        self.assertTrue('Editor' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))
        self.assertTrue('Owner' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))
        self.assertTrue('Reader' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))

        # Test the initial MAX properties
        max_community_info = self.get_max_context_info(community)
        self.assertEqual('helou', max_community_info.get(u'twitterHashtag', ''))
        self.assertFalse(max_community_info.get(u'notifications', False))
        self.assertTrue(u'[COMMUNITY]' in max_community_info.get('tags', []))

        for key in OPEN_PERMISSIONS:
            self.assertEqual(max_community_info['permissions'].get(key, ''), OPEN_PERMISSIONS[key])

    def test_community_creation_organizative(self):
        nom = u'community-test'
        description = 'Blabla'
        image = None
        community_type = 'Organizative'
        twitter_hashtag = 'helou'

        login(self.portal, 'ulearn.testuser1')

        self.portal.invokeFactory('ulearn.community', 'community-test',
                                 title=nom,
                                 description=description,
                                 image=image,
                                 community_type=community_type,
                                 twitter_hashtag=twitter_hashtag)

        community = self.portal['community-test']

        logout()

        # Test for the acl registry
        soup = get_soup('communities_acl', self.portal)
        # By the gwuuid
        records = [r for r in soup.query(Eq('gwuuid', IGWUUID(community).get()))]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].attrs.get('gwuuid', ''), IGWUUID(community).get())
        self.assertEqual(records[0].attrs.get('path', ''), '/'.join(community.getPhysicalPath()))
        self.assertEqual(records[0].attrs.get('hash', ''), sha1(community.absolute_url()).hexdigest())
        self.assertEqual(records[0].attrs.get('acl', '').get('users', [])[0]['role'], u'owner')
        self.assertEqual(records[0].attrs.get('acl', '').get('users', [])[0]['id'], u'ulearn.testuser1')

        # Test for internal objects
        self.assertEqual(community.objectIds(), ['documents', 'events', 'news'])

        # Test for photo folder
        self.assertEqual(community['documents'].objectIds(), ['media', ])

        # Test for subscribed users
        self.assertTrue(u'ulearn.testuser1' in self.get_max_subscribed_users(community))

        # Test for Plone permissions/local roles
        self.assertTrue('Reader' not in community.get_local_roles_for_userid(userid='AuthenticatedUsers'))
        self.assertTrue('Editor' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))
        self.assertTrue('Owner' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))
        self.assertTrue('Reader' in community.get_local_roles_for_userid(userid='ulearn.testuser1'))

        # Test the initial MAX properties
        max_community_info = self.get_max_context_info(community)
        self.assertEqual('helou', max_community_info.get(u'twitterHashtag', ''))
        self.assertFalse(max_community_info.get(u'notifications', False))
        self.assertTrue(u'[COMMUNITY]' in max_community_info.get('tags', []))

        for key in ORGANIZATIVE_PERMISSIONS:
            self.assertEqual(max_community_info['permissions'].get(key, ''), ORGANIZATIVE_PERMISSIONS[key])

    def test_community_creation_not_allowed(self):
        nom = u'community-test'
        description = 'Blabla'
        image = None
        community_type = 'Closed'
        twitter_hashtag = 'helou'

        login(self.portal, 'ulearn.testuser2')

        self.assertRaises(Unauthorized, self.portal.invokeFactory,
                          'ulearn.community', 'community-test',
                          title=nom,
                          description=description,
                          image=image,
                          community_type=community_type,
                          twitter_hashtag=twitter_hashtag)
        logout()

    def test_edit_community(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()
        community.twitter_hashtag = 'Modified'
        notify(ObjectModifiedEvent(community))
        max_community_info = self.get_max_context_info(community)
        self.assertEqual('modified', max_community_info.get(u'twitterHashtag', ''))

        community.notify_activity_via_push = True
        notify(ObjectModifiedEvent(community))
        max_community_info = self.get_max_context_info(community)
        self.assertEqual('posts', max_community_info.get(u'notifications', ''))

        community.notify_activity_via_push_comments_too = True
        notify(ObjectModifiedEvent(community))
        max_community_info = self.get_max_context_info(community)
        self.assertEqual('comments', max_community_info.get(u'notifications', ''))

        community.notify_activity_via_push = False
        community.notify_activity_via_push_comments_too = False
        notify(ObjectModifiedEvent(community))
        max_community_info = self.get_max_context_info(community)
        self.assertEqual('', max_community_info.get(u'notifications', ''))

    def test_edit_acl(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()
        acl = dict(users=[dict(id=u'janet.dura', displayName=u'Janet Durà', role=u'writer'),
                          dict(id=u'victor.fernandez', displayName=u'Víctor Fernández de Alba', role=u'reader')],
                   groups=[dict(id=u'PAS', displayName=u'PAS UPC', role=u'writer'),
                           dict(id=u'UPCnet', displayName=u'UPCnet', role=u'reader')]
                   )

        httpretty.enable()
        http_mock_hub_syncacl(acl, self.settings.hub_server)

        adapter = community.adapted()
        adapter.update_acl(acl)

        httpretty.disable()
        httpretty.reset()

        soup = get_soup('communities_acl', self.portal)
        records = [r for r in soup.query(Eq('gwuuid', IGWUUID(community).get()))]

        self.assertEqual(cmp(records[0].attrs['acl'], acl), 0)

    def test_events_visibility(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()

        login(self.portal, 'ulearn.testuser1')
        community['events'].invokeFactory('Event', 'test-event', title="Da event")
        logout()

        login(self.portal, 'ulearn.testuser2')

        pc = api.portal.get_tool('portal_catalog')

        self.assertFalse(pc.searchResults(portal_type='Event'))
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, 'community-test/events/test-event')

    def test_events_visibility_open_communities(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community(community_type='Open')

        login(self.portal, 'ulearn.testuser1')
        community['events'].invokeFactory('Event', 'test-event', title="Da event")
        logout()

        login(self.portal, 'ulearn.testuser2')

        pc = api.portal.get_tool('portal_catalog')

        self.assertEqual(len(pc.searchResults(portal_type='Event')), 0)

    def test_events_visibility_open_communities_switch_to_closed(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community(community_type='Open')

        community['events'].invokeFactory('Event', 'test-event', title="Da event")
        logout()

        login(self.portal, 'ulearn.testuser2')

        pc = api.portal.get_tool('portal_catalog')

        self.assertEqual(len(pc.searchResults(portal_type='Event')), 0)

        logout()

        login(self.portal, 'ulearn.testuser1')

        community.community_type = 'Closed'
        notify(ObjectModifiedEvent(community))

        logout()

        login(self.portal, 'ulearn.testuser2')

        self.assertFalse(pc.searchResults(portal_type='Event'))
        self.assertRaises(Unauthorized, self.portal.restrictedTraverse, 'community-test/events/test-event')

    # def test_newcommunities_getters_setters(self):
    #     readers = [u'victor.fernandez']
    #     subscribed = [u'janet.dura']
    #     community = self.create_test_community(id='community-test2', readers=readers, subscribed=subscribed)

    #     max_subs = self.get_max_subscribed_users(community)

    #     self.assertTrue(readers[0] in max_subs)
    #     self.assertTrue(subscribed[0] in max_subs)
    #     self.assertTrue(u'ulearn.testuser1' in max_subs)

    #     self.assertEqual(readers, community.readers)
    #     self.assertEqual(subscribed, community.subscribed)
    #     self.assertEqual([u'ulearn.testuser1'], community.owners)

    # def test_newcommunities_getters_setters_modify_subscriptions(self):
    #     readers = [u'victor.fernandez']
    #     subscribed = [u'janet.dura']
    #     community = self.create_test_community(id='community-test3', readers=readers, subscribed=subscribed)

    #     max_subs = self.get_max_subscribed_users(community)

    #     self.assertTrue(readers[0] in max_subs)
    #     self.assertTrue(subscribed[0] in max_subs)
    #     self.assertTrue(u'ulearn.testuser1' in max_subs)

    #     self.assertEqual(readers, community.readers)
    #     self.assertEqual(subscribed, community.subscribed)
    #     self.assertEqual([u'ulearn.testuser1'], community.owners)

    #     readers_state2 = [u'victor.fernandez', u'janet.dura']
    #     subscribed_state2 = []

    #     community.readers = readers_state2
    #     community.subscribed = subscribed_state2

    #     max_subs_state2 = self.get_max_subscribed_users(community)

    #     self.assertTrue(readers_state2[0] in max_subs_state2)
    #     self.assertTrue(readers_state2[1] in max_subs_state2)
    #     self.assertTrue(u'ulearn.testuser1' in max_subs_state2)

    #     readers_state3 = []
    #     subscribed_state3 = []

    #     community.readers = readers_state3
    #     community.subscribed = subscribed_state3

    #     max_subs_state3 = self.get_max_subscribed_users(community)

    #     self.assertEqual([u'ulearn.testuser1'], max_subs_state3)
    #     self.assertEqual(readers_state3, community.readers)
    #     self.assertEqual(subscribed_state3, community.subscribed)

    # def test_newcommunities_getters_setters_corner1(self):
    #     owners = [u'ulearn.testuser1']
    #     community = self.create_test_community(id='community-test4', owners=owners)

    #     max_subs = self.get_max_subscribed_users(community)

    #     self.assertTrue(u'ulearn.testuser1' in max_subs)

    #     self.assertEqual([u'ulearn.testuser1'], community.owners)

    # def test_open_community_join_getters_setters(self):
    #     subscribed = [u'janet.dura']
    #     community = self.create_test_community(id='community-test-open', community_type='Open', subscribed=subscribed)

    #     login(self.portal, 'victor.fernandez')

    #     toggle_subscribe = getMultiAdapter((community, self.request), name='toggle-subscribe')
    #     toggle_subscribe.render()

    #     max_subs = self.get_max_subscribed_users(community)
    #     self.assertTrue(u'victor.fernandez' in max_subs)

    #     toggle_subscribe.render()

    #     max_subs = self.get_max_subscribed_users(community)
    #     self.assertTrue(u'victor.fernandez' not in max_subs)

    #     logout()

    # def test_open_community_already_in_MAX_getters_setters(self):
    #     subscribed = [u'janet.dura']
    #     community = self.create_test_community(id='community-test-open-exist', community_type='Open', subscribed=subscribed)

    #     login(self.portal, 'victor.fernandez')

    #     toggle_subscribe = getMultiAdapter((community, self.request), name='toggle-subscribe')
    #     toggle_subscribe.render()

    #     max_subs = self.get_max_subscribed_users(community)
    #     self.assertTrue(u'victor.fernandez' in max_subs)
    #     self.assertTrue(u'janet.dura' in community.subscribed and u'victor.fernandez' in community.subscribed)
    #     self.assertTrue(u'ulearn.testuser1' in community.owners)

    #     toggle_subscribe.render()

    #     max_subs = self.get_max_subscribed_users(community)
    #     self.assertTrue(u'victor.fernandez' not in max_subs)
    #     self.assertTrue(u'janet.dura' in community.subscribed)
    #     self.assertTrue(u'ulearn.testuser1' in community.owners)

    #     logout()

    def test_notify_posts_comments(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community(id='community-test-notify', community_type='Open')

        info = self.get_max_context_info(community)

        self.assertEqual(info['notifications'], False)

        community.notify_activity_via_push = True

        notify(ObjectModifiedEvent(community))

        info = self.get_max_context_info(community)
        self.assertEqual(info['notifications'], u'posts')

        community.notify_activity_via_push_comments_too = True

        notify(ObjectModifiedEvent(community))

        info = self.get_max_context_info(community)
        self.assertEqual(info['notifications'], u'comments')

    def test_community_type_adapters(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community(id='community-test-notify', community_type='Closed')
        community.adapted()

    def test_delete_community(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()
        gwuuid = IGWUUID(community).get()
        api.content.delete(obj=community)

        soup = get_soup('communities_acl', self.portal)
        records = [r for r in soup.query(Eq('gwuuid', gwuuid))]

        self.assertFalse(records)

    def test_auto_subscribe_to_open(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community(community_type='Open')
        logout()
        login(self.portal, 'ulearn.testuser2')

        self.request.method = 'POST'
        view = getMultiAdapter((community, self.request), name='subscribe')
        result = view.render()

        result = json.loads(result)
        self.assertTrue('message' in result)

        adapter = community.adapted()
        acl = adapter.get_acl()
        self.assertTrue(len(acl['users']), 2)
        users_subscribed = [a['id'] for a in acl['users']]
        self.assertTrue(u'ulearn.testuser2' in users_subscribed)

        self.assertTrue(u'ulearn.testuser2' in self.get_max_subscribed_users(community))

    def test_acl_migration(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()

        # Fake already existing old style acl
        community.readers = ['ulearn.testuser2', 'janet.dura']
        community.subscribed = ['javier.otero']
        community.owners = ['victor.fernandez']

        view = getMultiAdapter((self.portal, self.request), name='migrate_acls')
        view.render()

        adapter = community.adapted()
        acl = adapter.get_acl()

        readers = [a['id'] for a in acl['users'] if a['role'] == u'reader']
        writers = [a['id'] for a in acl['users'] if a['role'] == u'writer']
        owners = [a['id'] for a in acl['users'] if a['role'] == u'owner']

        self.assertTrue(u'janet.dura' in readers)
        self.assertTrue(u'ulearn.testuser2' in readers)
        self.assertTrue(u'javier.otero' in writers)
        self.assertTrue(u'victor.fernandez' in owners)

        self.assertEqual(len(readers), 2)
        self.assertEqual(len(writers), 1)
        self.assertEqual(len(owners), 1)

    def test_interactions_type_d(self):
        """ The interactions type D are those generated by user interaction
            programatically or using uLearnHUB directly
        """
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community()

        self.request.method = 'POST'
        base_request = {'action': 'subscribe',
                        'username': 'victor.fernandez',
                        'subscription': {
                            'permissions': [
                                'read',
                                'write',
                                'unsubscribe']}
                        }
        self.request['BODY'] = json.dumps(base_request)

        view = getMultiAdapter((community, self.request), name='notify')
        view.render()

        adapter = community.adapted()
        acl = adapter.get_acl()

        users_subscribed = [a['id'] for a in acl['users']]

        self.assertTrue(u'victor.fernandez' in users_subscribed)
        self.assertTrue('Editor' in community.get_local_roles_for_userid(userid='victor.fernandez'))

        base_request['action'] = 'change_permissions'
        base_request['subscription']['permissions'] = ['read', ]

        self.request['BODY'] = json.dumps(base_request)
        view.render()
        acl = adapter.get_acl()

        self.assertTrue('Reader' in community.get_local_roles_for_userid(userid='victor.fernandez'))
        self.assertTrue('Editor' not in community.get_local_roles_for_userid(userid='victor.fernandez'))

        base_request['action'] = 'unsubscribe'

        self.request['BODY'] = json.dumps(base_request)

        view.render()
        acl = adapter.get_acl()
        users_subscribed = [a['id'] for a in acl['users']]

        self.assertTrue(u'victor.fernandez' not in users_subscribed)
        self.assertTrue('Reader' not in community.get_local_roles_for_userid(userid='victor.fernandez'))
        self.assertTrue('Editor' not in community.get_local_roles_for_userid(userid='victor.fernandez'))
