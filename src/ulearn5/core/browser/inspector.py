# -*- coding: utf-8 -*-
from five import grok
from zope.component.hooks import getSite

from Products.CMFPlone.interfaces import IPloneSiteRoot

from ulearn5.core.interfaces import IUlearn5CoreLayer


import inspect
import importlib

# MODULES_TO_INSPECT = ['genweb.core.browser.setup',
#                       'ulearn5.core.browser.setup',
#                       'ulearn.core.browser.migrations']

MODULES_TO_INSPECT = ['base5.core.browser.setup',
                      'ulearn5.core.browser.setup']

grok.templatedir("inspector_templates")

class clouseau(grok.View):
    grok.name('clouseau')
    grok.template('clouseau')
    grok.context(IPloneSiteRoot)
    grok.layer(IUlearn5CoreLayer)

    def get_templates(self):
        portal = getSite()

        urls = []

        for module in MODULES_TO_INSPECT:
            themodule = importlib.import_module(module)
            members = inspect.getmembers(themodule, inspect.isclass)

            for name, klass in members:
                if grok.View in klass.__bases__:
                    urls.append('{}/{}'.format(portal.absolute_url(), name.lower()))

        return urls
