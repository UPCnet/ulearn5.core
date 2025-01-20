# -*- coding: utf-8 -*-
import unittest2 as unittest
from plone import api
from zope.component import getMultiAdapter

from zope.component import getUtility
from zope.interface import implementer
from zope.component import provideUtility
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from souper.interfaces import ICatalogFactory
from souper.soup import NodeAttributeIndexer
from repoze.catalog.query import Eq
from repoze.catalog.query import Or
from repoze.catalog.query import And
from souper.soup import get_soup

from plone.app.testing import login
from plone.app.testing import logout
from plone.app.testing import setRoles

from base5.core.utils import reset_user_catalog
from base5.core.utils import add_user_to_catalog

from ulearn5.core.tests import uLearnTestBase
from ulearn5.core.browser.searchuser import searchUsersFunction
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING
from mrs5.max.utilities import IMAXClient

import json
import os
from six.moves import range


class TestExample(uLearnTestBase):

    layer = ULEARN5_CORE_INTEGRATION_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        self.maxclient, settings = getUtility(IMAXClient)()
        self.username = settings.max_restricted_username
        self.token = settings.max_restricted_token

        self.maxclient.setActor(settings.max_restricted_username)
        self.maxclient.setToken(settings.max_restricted_token)

    def tearDown(self):
        self.maxclient.contexts['http://nohost/plone/community-testsearch'].delete()

    def create_default_test_users(self):
        for suffix in range(1, 15):
            api.user.create(email='test@upcnet.es', username='victor.fernandez.' + str(suffix),
                            properties=dict(fullname='Víctor' + str(suffix),
                                            location='Barcelona',
                                            ubicacio='NX',
                                            email='test@upcnet.es'))

    def delete_default_test_users(self):
        for suffix in range(1, 15):
            api.user.delete(username='victor.fernandez.' + str(suffix))

    def test_default_search(self):
        login(self.portal, 'ulearn.testuser1')
        users = searchUsersFunction(self.portal, self.request, '')
        logout()

        self.assertTrue(len(users['content']) == 3)

    def test_search_portal_with_search_string(self):
        search_string = 'janet'
        login(self.portal, 'ulearn.testuser1')
        users = searchUsersFunction(self.portal, self.request, search_string)
        logout()

        self.assertTrue(len(users['content']) == 1)
        self.assertEqual(users['content'][0]['id'], 'janet.dura')

    def test_search_portal_with_search_string_not_username(self):
        search_string = 'Janet'
        login(self.portal, 'ulearn.testuser1')
        users = searchUsersFunction(self.portal, self.request, search_string)
        logout()

        self.assertTrue(len(users['content']) == 1)
        self.assertEqual(users['content'][0]['id'], 'janet.dura')

    def test_search_portal_with_search_string_unicode(self):
        search_string = 'Durà'
        login(self.portal, 'ulearn.testuser1')
        users = searchUsersFunction(self.portal, self.request, search_string)
        logout()

        self.assertTrue(len(users['content']) == 1)
        self.assertEqual(users['content'][0]['id'], 'janet.dura')

    def test_search_community(self):
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community(id='community-testsearch', community_type='Closed')

        users = searchUsersFunction(community, self.request, '')

        self.assertTrue(len(users['content']) == 1)
        self.assertEqual(users['content'][0]['id'], 'ulearn.testuser1')

        users = searchUsersFunction(community, self.request, 'janet')

        self.assertTrue(len(users['content']) == 0)

        # community.subscribed = [u'janet.dura', u'ulearn.testuser1']

        # users = searchUsersFunction(community, self.request, '')
        # self.assertTrue(len(users['content']) == 2)

        # users = searchUsersFunction(community, self.request, 'janet')
        # self.assertTrue(len(users['content']) == 1)

        logout()

    def test_search_community_with_additional_fields_on_community_no_query(self):
        """ This is the case when a client has customized user properties """
        login(self.portal, 'ulearn.testuser1')
        community = self.create_test_community(id='community-testsearch', community_type='Closed')

        users = searchUsersFunction(community, self.request, '')

        self.assertTrue(len(users['content']) == 1)
        self.assertEqual(users['content'][0]['id'], 'ulearn.testuser1')

        logout()

    def test_search_community_with_additional_fields_on_portal_with_query(self):
        """ This is the case when a client has customized user properties """
        login(self.portal, 'ulearn.testuser1')
        # We provide here the required initialization for a user custom properties catalog
        provideUtility(TestUserExtendedPropertiesSoupCatalogFactory(), name='user_properties_exttest')
        api.portal.set_registry_record(name='base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender', value='user_properties_exttest')

        # Modify an user to accomodate new properties from extended catalog
        # Force it as we are not faking the extension of the user properties
        # (Plone side utility overriding blabla)
        add_user_to_catalog('ulearn.testuser1', {'position': 'Jefe', 'unit_organizational': 'Finance'})

        users = searchUsersFunction(self.portal, self.request, 'ulearn.testuser1')

        self.assertTrue(len(users['content']) == 1)
        self.assertEqual(users['content'][0]['id'], 'ulearn.testuser1')
        self.assertEqual(users['content'][0]['position'], 'Jefe')
        self.assertEqual(users['content'][0]['unit_organizational'], 'Finance')

        logout()

    def test_user_search_on_acl(self):
        """
            cas 1: Primer caràcter (només 1) is_useless_request == False too_much_results ? searching_surname == False
            cas 2.1: Segona lletra en endavant i not searching_surname i is_useless_request i too_much_results ==> soup
            cas 2.1: Segona lletra en endavant i not searching_surname i is_useless_request i not too_much_results ==> MAX
            cas 2.2: Segona lletra en endavant i not searching_surname i not is_useless_request ==> Seguim filtrant query soup
            cas 3: Segona lletra  en endavant i searching_surname i not is_useless_request ==> soup
            cas 3: Segona lletra  en endavant i searching_surname i is_useless_request ==> MAX

            First request, no additional last_query nor last_query_count
            Create a bunch of users into the system, but clearing the catalog
            Only one remains
        """
        self.create_default_test_users()
        reset_user_catalog()
        add_user_to_catalog('victor.fernandez', dict(fullname='Víctor'))

        login(self.portal, 'ulearn.testuser1')

        search_view = getMultiAdapter((self.portal, self.request), name='omega13usersearch')
        self.request.form = dict(q='v')
        result = search_view.render()
        result = json.loads(result)
        self.assertEqual(result['last_query_count'], 1)
        self.assertEqual(result['last_query'], 'v')

        # Force the search to be useless to force a MAX update
        self.request.form = dict(q='victor.fer', last_query='v', last_query_count=1)
        result = search_view.render()
        result = json.loads(result)

        self.assertTrue(result['last_query_count'] > 5)
        self.assertEqual(result['last_query'], 'victor.fer')

        soup = get_soup('user_properties', self.portal)
        self.assertTrue(len([r for r in soup.query(Eq('username', 'victor fer*'))]) > 5)

        # Amb un altre usuari (janet)
        add_user_to_catalog('janet.dura', dict(fullname='Janet'))
        self.request.form = dict(q='janet', last_query='', last_query_count=0)
        result = search_view.render()
        result = json.loads(result)

        self.assertEqual(result['last_query_count'], 1)
        self.assertEqual(result['results'], [{'displayName': 'Janet', 'id': 'janet.dura'}])

        self.request.form = dict(q='janeth', last_query='janet', last_query_count=1)
        result = search_view.render()
        result = json.loads(result)
        self.assertEqual(result['last_query_count'], 0)

        # Freeze this part as we cannot rely in that user being always there
        # self.request.form = dict(q='janeth.tosca', last_query='janeth', last_query_count=0)
        # result = search_view.render()
        # result = json.loads(result)

        # self.assertEqual(result['last_query_count'], 1)
        # self.assertEqual(result['results'], [{"displayName": "janeth.toscana", "id": "janeth.toscana"}])

        logout()

        login(self.portal, 'admin')
        self.delete_default_test_users()
        logout()

    def test_user_properties_searchable_text(self):
        """ Test the searchable_text of the user_properties soup for make sure
            you can search on several properties at once.
        """
        self.create_default_test_users()
        reset_user_catalog()
        add_user_to_catalog('victor.fernandez', dict(fullname='Víctor Fernández de Alba', location='Nexus'))

        login(self.portal, 'ulearn.testuser1')

        soup = get_soup('user_properties', self.portal)
        self.assertTrue([r for r in soup.query(Eq('searchable_text', 'victor Nex*'))])
        logout()

        login(self.portal, 'admin')
        self.delete_default_test_users()
        logout()

    @unittest.skipUnless(os.environ.get('LDAP_TEST', False), 'Skipping due to lack of LDAP access')
    def test_group_search_on_acl(self):
        setRoles(self.portal, 'ulearn.testuser1', ['Manager'])
        login(self.portal, 'ulearn.testuser1')
        sync_view = getMultiAdapter((self.portal, self.request), name='syncldapgroups')
        sync_view.render()
        logout()

        login(self.portal, 'ulearn.testuser2')
        search_view = getMultiAdapter((self.portal, self.request), name='omega13groupsearch')
        self.request.form = dict(q='pas')
        result = search_view.render()
        result = json.loads(result)

        self.assertTrue(len(result['results']) > 5)
        self.assertTrue('PAS' in [r['id'] for r in result['results']])

    @unittest.skipUnless(os.environ.get('LDAP_TEST', False), 'Skipping due to lack of LDAP access')
    def test_group_search_on_acl_with_dashes(self):
        setRoles(self.portal, 'ulearn.testuser1', ['Manager'])
        login(self.portal, 'ulearn.testuser1')
        sync_view = getMultiAdapter((self.portal, self.request), name='syncldapgroups')
        sync_view.render()
        logout()

        login(self.portal, 'ulearn.testuser2')
        search_view = getMultiAdapter((self.portal, self.request), name='omega13groupsearch')
        self.request.form = dict(q='pas-188')
        result = search_view.render()
        result = json.loads(result)

        self.assertTrue(len(result['results']) == 2)

    def test_user_legit_mode(self):
        """
        """
        self.create_default_test_users()
        reset_user_catalog()
        # Add a legit user
        add_user_to_catalog('victor.fernandez', dict(fullname='Víctor'))
        normalized_query = 'victor fer*'
        soup = get_soup('user_properties', self.portal)

        # Search for it via the searchable_text
        result = [r for r in soup.query(Eq('searchable_text', normalized_query))]
        self.assertEqual(result[0].attrs['id'], 'victor.fernandez')
        self.assertEqual(len(result), 1)

        # Add a non legit user from the initial set
        add_user_to_catalog('victor.fernandez.1', dict(fullname='Víctor'), notlegit=True)

        # The result is still the legit one alone
        result = [r for r in soup.query(Eq('searchable_text', normalized_query))]
        self.assertEqual(result[0].attrs['id'], 'victor.fernandez')
        self.assertEqual(len(result), 1)

        # The non legit only can be accessed directly by querying the notlegit
        # index and the legit one does not show, of course
        result = [r for r in soup.query(Eq('notlegit', True))]
        self.assertEqual(result[0].attrs['id'], 'victor.fernandez.1')
        self.assertEqual(len(result), 1)

        # The non legit only can be accessed directly by querying the fields
        # directly
        result = [r for r in soup.query(And(Or(Eq('username', normalized_query), Eq('fullname', normalized_query)), Eq('notlegit', True)))]
        self.assertEqual(result[0].attrs['id'], 'victor.fernandez.1')
        self.assertEqual(len(result), 1)

        # If the non legit became legit at some point of time via a subscriber
        api.user.get('victor.fernandez.1').setMemberProperties(mapping={'fullname': 'Test', 'location': 'Barcelona', 'telefon': '654321 123 123'})

        # Then it does not show as not legit
        result = [r for r in soup.query(And(Or(Eq('username', normalized_query), Eq('fullname', normalized_query)), Eq('notlegit', True)))]
        self.assertEqual(len(result), 0)

        # And it shows as legit
        result = [r for r in soup.query(Eq('searchable_text', normalized_query))]
        self.assertEqual(len(result), 2)

    def test_rebuild_user_catalog_with_user_extended_properties(self):
        """ This is the case when a client has customized user properties """
        login(self.portal, 'ulearn.testuser1')
        # We provide here the required initialization for a user custom properties catalog
        provideUtility(TestUserExtendedPropertiesSoupCatalogFactory(), name='user_properties_exttest')
        api.portal.set_registry_record(name='base5.core.controlpanel.core.IBaseCoreControlPanelSettings.user_properties_extender', value='user_properties_exttest')

        # Fake extended Plone user properties
        pmd = api.portal.get_tool('portal_memberdata')
        pmd._setProperty('position', '')
        pmd._setProperty('unit_organizational', '')

        # Modify user
        api.user.get('ulearn.testuser1').setMemberProperties(mapping={'position': 'Jefe', 'unit_organizational': 'Finance'})

        rebuild_view = getMultiAdapter((self.portal, self.request), name='rebuild_user_catalog')
        rebuild_view.render()

        users_view = getMultiAdapter((self.portal, self.request), name='view_user_catalog')
        users = json.loads(users_view.render())

        self.assertTrue('unit_organizational' in users['ulearn.testuser1'])
        self.assertTrue(users['ulearn.testuser1']['unit_organizational'] == 'Finance')

        # Then, reset and rebuild
        reset_view = getMultiAdapter((self.portal, self.request), name='reset_user_catalog')
        reset_view.render()
        rebuild_view.render()

        users = json.loads(users_view.render())

        self.assertTrue('unit_organizational' in users['ulearn.testuser1'])
        self.assertTrue(users['ulearn.testuser1']['unit_organizational'] == 'Finance')


@implementer(ICatalogFactory)
class TestUserExtendedPropertiesSoupCatalogFactory(object):
    """ Extended user catalog for testing purposes
    """
    properties = ['username', 'unit_organizational', 'position']

    # The profile properties for display on the user profile, including the
    # default ones, and in order
    profile_properties = ['unit_organizational', 'twitter_username']

    # The directory properties for display on the directory views
    directory_properties = ['email', 'telefon', 'location', 'ubicacio', 'position']
    directory_icons = {'email': 'fa fa-envelope', 'telefon': 'fa fa-mobile', 'location': 'fa fa-building-o', 'ubicacio': 'fa fa-user', 'position': 'fa fa-user'}

    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id')
        catalog['id'] = CatalogFieldIndex(idindexer)
        userindexer = NodeAttributeIndexer('username')
        catalog['username'] = CatalogTextIndex(userindexer)
        unit_organizational = NodeAttributeIndexer('unit_organizational')
        catalog['unit_organizational'] = CatalogTextIndex(unit_organizational)
        position = NodeAttributeIndexer('position')
        catalog['position'] = CatalogTextIndex(position)
        return catalog
