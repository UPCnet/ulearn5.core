# -*- coding: utf-8 -*-
from five import grok
from plone import api

from Acquisition import aq_inner
from OFS.interfaces import IApplication
from OFS.interfaces import IFolder
from plone.subrequest import subrequest
from Products.CMFPlone.interfaces import IPloneSiteRoot
from Products.CMFCore.utils import getToolByName
from zope.interface import alsoProvides

import urllib.request, urllib.parse, urllib.error


class installPloneProduct(grok.View):
    """ Install a product passed by form parameter in the current Plone site.
        /install_product?product_name=ulearn5.core
    """
    grok.context(IPloneSiteRoot)
    grok.name('install_product')
    grok.require('cmf.ManagePortal')

    def render(self, portal=None):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        
        if not portal:
            portal = api.portal.get()

        product_name = self.request.form['product_name']
        output = []
        qi = getToolByName(portal, 'portal_quickinstaller')

        if qi.isProductAvailable(product_name):
            qi.installProducts([product_name], reinstall=True)
            output.append('{}: Successfully installed {}'.format(portal.id, product_name))
        return '\n'.join(output)


class reinstallPloneProduct(grok.View):
    """ Reinstalls a product passed by form parameter in the current Plone site.
        /reinstall_product?product_name=ulearn5.core
    """
    grok.context(IPloneSiteRoot)
    grok.name('reinstall_product')
    grok.require('cmf.ManagePortal')

    def render(self, portal=None):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        
        if not portal:
            portal = api.portal.get()

        product_name = self.request.form['product_name']
        output = []
        qi = getToolByName(portal, 'portal_quickinstaller')

        if qi.isProductInstalled(product_name):
            qi.uninstallProducts([product_name, ], reinstall=True)
            qi.installProducts([product_name], reinstall=True)
            output.append('{}: Successfully reinstalled {}'.format(portal.id, product_name))
        return '\n'.join(output)


class uninstallPloneProduct(grok.View):
    """ Uninstall a product passed by form parameter in the current Plone site.
        /uninstall_product?product_name=ulearn5.etherpad
    """
    grok.context(IPloneSiteRoot)
    grok.name('uninstall_product')
    grok.require('cmf.ManagePortal')

    def render(self, portal=None):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        if not portal:
            portal = api.portal.get()

        product_name = self.request.form['product_name']
        output = []
        qi = getToolByName(portal, 'portal_quickinstaller')

        if qi.isProductInstalled(product_name):
            qi.uninstallProducts([product_name, ], reinstall=False)
            output.append('{}: Successfully uninstalled {}'.format(portal.id, product_name))
        return '\n'.join(output)


def listPloneSites(zope):
    """ List the available plonesites to be used by other function """
    out = []
    for item in list(zope.values()):
        if IFolder.providedBy(item) and not IPloneSiteRoot.providedBy(item):
            for site in list(item.values()):
                if IPloneSiteRoot.providedBy(site):
                    out.append(site)
        elif IPloneSiteRoot.providedBy(item):
            out.append(item)
    return out


class bulkExecuteScriptView(grok.View):
    """ Execute one action view in all instances passed as a form parameter 
        http:/maquina:puerto/bulk_action?view=reinstall_product&product_name=ulearn5.core&exclude_sites=Plone
    """
    grok.context(IApplication)
    grok.name('bulk_action')
    grok.require('cmf.ManagePortal')

    def render(self):
        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        context = aq_inner(self.context)
        args = self.request.form
        view_name = self.request.form['view']
        exclude_sites = self.request.form.get('exclude_sites', '').split(',')
        plonesites = listPloneSites(context)
        output = []
        for plonesite in plonesites:
            if plonesite.id not in exclude_sites:
                print('======================')
                print(('Executing view in {}'.format(plonesite.id)))
                print('======================')
                quoted_args = urllib.parse.urlencode(args)
                response = subrequest('/'.join(plonesite.getPhysicalPath()) + '/{}?{}'.format(view_name, quoted_args))
                output.append("""<br/>-- Executed view {} in site {} --""".format(view_name, plonesite.id))
                output.append(response.getBody())
        return '\n'.join(output)