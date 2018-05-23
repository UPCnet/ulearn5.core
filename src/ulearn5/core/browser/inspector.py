# -*- coding: utf-8 -*-
from five import grok
from zope.component.hooks import getSite

from Products.CMFPlone.interfaces import IPloneSiteRoot

from ulearn5.core.interfaces import IUlearn5CoreLayer


import inspect
import importlib


MODULES_TO_INSPECT = ['base5.core.setup',
                      'ulearn5.core.browser.setup']

grok.templatedir("inspector_templates")

class clouseau(grok.View):
    grok.name('clouseau')
    grok.template('clouseau')
    grok.context(IPloneSiteRoot)
    grok.layer(IUlearn5CoreLayer)
    grok.require('cmf.ManagePortal')

    def get_helpers(self):
        portal = getSite()
        app = portal.restrictedTraverse('/')

        plone_site = []
        application = []

        for module in MODULES_TO_INSPECT:
            themodule = importlib.import_module(module)
            members = inspect.getmembers(themodule, inspect.isclass)

            for name, klass in members:
                if grok.View in klass.__bases__:
                    if getattr(klass, 'grokcore.component.directive.context').getName() == 'IApplication':
                        application.append(dict(url='{}/{}'.format(app.absolute_url(), getattr(klass, 'grokcore.component.directive.name', name.lower())), description=klass.__doc__))
                    else:
                        plone_site.append(dict(url='{}/{}'.format(portal.absolute_url(), getattr(klass, 'grokcore.component.directive.name', name.lower())), description=klass.__doc__))

        return (plone_site, application)
