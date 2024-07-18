# -*- coding: utf-8 -*-
from Acquisition import aq_inner
from five import grok
from infrae.rest.components import ALLOWED_REST_METHODS
from infrae.rest.components import lookupREST
from infrae.rest.interfaces import RESTMethodPublishedEvent
from plone import api
from Products.CMFPlone.interfaces import IPloneSiteRoot
from ulearn5.core.api import queryRESTComponent
from ulearn5.core.content.community import ICommunity
from zExceptions import NotFound
from zope.event import notify
import logging

logger = logging.getLogger(__name__)


class APIRoot(grok.View):
    grok.context(IPloneSiteRoot)
    grok.require('base.authenticated')
    grok.name('api')

    def publishTraverse(self, request, name):
        """You can traverse to a method called the same way that the
        HTTP method name, or a sub view
        """
        if name in ALLOWED_REST_METHODS and name == request.method:
            if hasattr(self, name):
                notify(RESTMethodPublishedEvent(self, name))
                return getattr(self, name)

        view = queryRESTComponent(
            (self, self.context),
            (self.context, request),
            name=name,
            parent=self)
        if view is None:
            raise NotFound(name)
        return view

    def render(self):
        return 'uShare Communities REST Api'
        return lookupREST(self.context, self.request, 'api_root')


def urlBelongsToCommunity(url, portal_url):
    tree_site = api.portal.get()
    partial_path = url.split(portal_url)[1]
    partial_path.replace('#', '')  # Sanitize if necessary
    if partial_path.endswith('/view/'):
        partial_path = partial_path.split('/view/')[0]
    elif partial_path.endswith('/view'):
        partial_path = partial_path.split('/view')[0]
    partial_path = partial_path.encode('utf-8')
    segments = partial_path.split('/')
    leafs = [segment for segment in segments if segment]
    for leaf in leafs:
        try:
            obj = aq_inner(tree_site.unrestrictedTraverse(leaf))
            if (ICommunity.providedBy(obj)):
                return True
            else:
                tree_site = obj
        except:
            logger.error('Error in retrieving object: %s' % url)

    return False
