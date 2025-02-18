# -*- coding: utf-8 -*-
import os

import unittest2 as unittest
from mrs5.max.utilities import IMAXClient
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING
from ulearn5.core.tests import uLearnTestBase
from ulearn5.core.utils import get_or_initialize_annotation
from zope.component import getMultiAdapter, getUtility


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

        ldap_groups = get_or_initialize_annotation('ldap_groups')
        self.assertTrue(len(list(ldap_groups.keys())) > 0)

