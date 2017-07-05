# -*- coding: utf-8 -*-
import unittest2 as unittest
from hashlib import sha1
from plone import api
from AccessControl import Unauthorized
from zope.event import notify
from zope.lifecycleevent import ObjectModifiedEvent
from zope.component import getUtility
from zope.component import getMultiAdapter
from zope.component import getAdapter
from base5.core.utilities import IElasticSearch

from ulearn5.core.tests import uLearnTestBase
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING
from ulearn5.core.browser.sharing import ElasticSharing

import os
import time


class TestExample(uLearnTestBase):

    layer = ULEARN5_CORE_INTEGRATION_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']
        api.portal.set_registry_record('genweb.controlpanel.core.IGenwebCoreControlPanelSettings.elasticsearch',
                                       u'http://pc60012.estacions.upcnet.es:9200')
        self.elastic = getUtility(IElasticSearch)
        self.elastic.create_new_connection()
        self.elastic().indices.create(index=ElasticSharing().get_index_name())

    def tearDown(self):
        self.elastic().indices.delete(index=ElasticSharing().get_index_name())

    @unittest.skipUnless(os.environ.get('ES_TEST', False), 'Skipping due to lack of ES access')
    def test_make_record(self):
        folder = api.content.create(container=self.portal, type='Folder', title='Test folder')
        api.user.grant_roles(username='janet.dura', obj=folder, roles=['Editor'])
        record = ElasticSharing().make_record(folder, 'janet.dura')

        self.assertTrue(record['index'].startswith('security.plone'))
        self.assertTrue('Editor' in record['body']['roles'])
        self.assertTrue(record['body']['path'] == '/test-folder')
        self.assertTrue(record['body']['principal'] == 'janet.dura')

    @unittest.skipUnless(os.environ.get('ES_TEST', False), 'Skipping due to lack of ES access')
    def test_add_modify_delete_record(self):
        folder = api.content.create(container=self.portal, type='Folder', title='Test folder')
        api.user.grant_roles(username='janet.dura', obj=folder, roles=['Editor'])
        ElasticSharing().add(folder, 'janet.dura')

        time.sleep(1)

        result = self.elastic().search(index=ElasticSharing().get_index_name(),
                                       doc_type='sharing',
                                       body={'query': {'match': {'principal': 'janet.dura'}}})

        self.assertTrue(result['hits']['total'] == 1)

        api.user.grant_roles(username='janet.dura', obj=folder, roles=['Manager'])
        ElasticSharing().modify(folder, 'janet.dura', dict(roles=api.user.get_roles(username='janet.dura', obj=folder)))

        ElasticSharing().remove(folder, 'janet.dura')

        time.sleep(1)
        result = self.elastic().search(index=ElasticSharing().get_index_name(),
                                       doc_type='sharing',
                                       body={'query': {'match': {'principal': 'janet.dura'}}})

        self.assertTrue(result['hits']['total'] == 0)

    def test_get(self):
        folder = api.content.create(container=self.portal, type='Folder', title='Test folder')
        api.user.grant_roles(username='janet.dura', obj=folder, roles=['Editor'])
        ElasticSharing().add(folder, 'janet.dura')
        time.sleep(1)

        result = ElasticSharing().get(folder, 'janet.dura')
        self.assertTrue('Editor' in result['roles'])
        self.assertTrue(result['path'] == '/test-folder')
        self.assertTrue(result['principal'] == 'janet.dura')
