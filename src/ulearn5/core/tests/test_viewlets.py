# -*- coding: utf-8 -*-
from ulearn5.core.tests import uLearnTestBase
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING
from ulearn5.theme.browser.viewlets import gwCSSViewlet
from ulearn5.js.browser.viewlets import gwJSViewlet

import json
import pkg_resources


class TestExample(uLearnTestBase):

    layer = ULEARN5_CORE_INTEGRATION_TESTING

    def setUp(self):
        self.app = self.layer['app']
        self.portal = self.layer['portal']
        self.request = self.layer['request']

        ulearnthemeegg = pkg_resources.get_distribution('ulearn5.theme')
        ulearnjsegg = pkg_resources.get_distribution('ulearn.js')

        resource_file_css = open('{}/ulearn/theme/config.json'.format(ulearnthemeegg.location))
        resource_file_js = open('{}/ulearn/js/config.json'.format(ulearnjsegg.location))
        self.resources_conf_css = json.loads(resource_file_css.read())
        self.resources_conf_js = json.loads(resource_file_js.read())

    def test_css_development_resource_viewlet(self):

        viewlet = gwCSSViewlet(self.portal, self.request, None, None)
        viewlet.update()
        resources = viewlet.get_development_resources()

        for resource in resources:
            self.assertTrue('++' in resource)

    def test_css_production_resource_viewlet(self):
        viewlet = gwCSSViewlet(self.portal, self.request, None, None)
        viewlet.update()
        resources = viewlet.get_production_resources()

        for resource in resources:
            self.assertTrue('++' in resource)

        self.assertTrue(len(resources) == len(self.resources_conf_css['order']))

    def test_js_development_resource_viewlet(self):

        viewlet = gwJSViewlet(self.portal, self.request, None, None)
        viewlet.update()
        resources = viewlet.get_development_resources()

        for resource in resources:
            self.assertTrue('++' in resource)

    def test_js_production_resource_viewlet(self):
        viewlet = gwJSViewlet(self.portal, self.request, None, None)
        viewlet.update()
        resources = viewlet.get_production_resources()

        for resource in resources:
            self.assertTrue('++' in resource)

        self.assertTrue(len(resources) == len(self.resources_conf_js['order']))
