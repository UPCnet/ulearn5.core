# -*- coding: utf-8 -*-
import os

import unittest2 as unittest
from mrs5.max.utilities import IMAXClient
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING
from ulearn5.core.tests import uLearnTestBase
from zope.component import getMultiAdapter, getUtility
from souper.soup import get_soup

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

    @unittest.skipUnless(os.environ.get('LDAP_TEST', False), 'Skipping due to lack of LDAP access')
    def test_group_sync(self):
        sync_view = getMultiAdapter((self.portal, self.request), name='syncldapgroups')
        sync_view.render()

        soup = get_soup('ldap_groups', self.portal)

        self.assertTrue(len(soup.data.keys()) > 0)
