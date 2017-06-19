# -*- coding: utf-8 -*-
"""Setup tests for this package."""
from plone import api
from ulearn5.core.testing import ULEARN5_CORE_INTEGRATION_TESTING  # noqa

import unittest


class TestSetup(unittest.TestCase):
    """Test that ulearn5.core is properly installed."""

    layer = ULEARN5_CORE_INTEGRATION_TESTING

    def setUp(self):
        """Custom shared utility setup for tests."""
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')

    def test_product_installed(self):
        """Test if ulearn5.core is installed."""
        self.assertTrue(self.installer.isProductInstalled(
            'ulearn5.core'))

    def test_browserlayer(self):
        """Test that IUlearn5CoreLayer is registered."""
        from ulearn5.core.interfaces import (
            IUlearn5CoreLayer)
        from plone.browserlayer import utils
        self.assertIn(IUlearn5CoreLayer, utils.registered_layers())


class TestUninstall(unittest.TestCase):

    layer = ULEARN5_CORE_INTEGRATION_TESTING

    def setUp(self):
        self.portal = self.layer['portal']
        self.installer = api.portal.get_tool('portal_quickinstaller')
        self.installer.uninstallProducts(['ulearn5.core'])

    def test_product_uninstalled(self):
        """Test if ulearn5.core is cleanly uninstalled."""
        self.assertFalse(self.installer.isProductInstalled(
            'ulearn5.core'))

    def test_browserlayer_removed(self):
        """Test that IUlearn5CoreLayer is removed."""
        from ulearn5.core.interfaces import \
            IUlearn5CoreLayer
        from plone.browserlayer import utils
        self.assertNotIn(IUlearn5CoreLayer, utils.registered_layers())
