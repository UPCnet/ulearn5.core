# -*- coding: utf-8 -*-
from Products.CMFPlone.interfaces import IPloneSiteRoot

from five import grok
from plone import api
from plone.registry.interfaces import IRegistry
from zope.component import queryUtility

from ulearn5.core.api import ApiResponse
from ulearn5.core.api import REST
from ulearn5.core.api import api_resource
from ulearn5.core.api.root import APIRoot
from ulearn5.core.controlpanel import IUlearnControlPanelSettings


def calculatePortalTypeOfInternalPath(url, portal_url):
    site = api.portal.get()
    base_path = '/'.join(site.getPhysicalPath())
    partial_path = url.split(portal_url)[1]
    partial_path.replace('#', '') # Sanitize if necessary
    if partial_path.endswith('/view/'):
        partial_path = partial_path.split('/view/')[0]
    elif partial_path.endswith('/view'):
        partial_path = partial_path.split('/view')[0]
    custom_path = base_path + partial_path.encode('utf-8')
    nextObj = api.content.get(path=custom_path)
    return nextObj.Type()


class Banners(REST):
    """
        /api/banners
    """

    grok.adapts(APIRoot, IPloneSiteRoot)
    grok.require('base.authenticated')

    @api_resource(required_roles=['Member', 'Manager', 'Api'])
    def GET(self):
        """ Return all banners. """
        results = api.content.find(
            portal_type="ulearn.banner",
            review_state=['intranet'],
            sort_order='descending',
            sort_on='getObjPositionInParent',
            )

        banners = []

        portal = api.portal.get()
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        if ulearn_tool.url_site == None or ulearn_tool.url_site == '':
            portal_url = portal.absolute_url()
        else:
            portal_url = ulearn_tool.url_site

        for result in results:
            obj = result.getObject()
            if '/search' in obj.url:
                continue

            internal = True if obj.url.startswith(portal_url) else False

            link = obj.url.replace('#', '') if internal else obj.url
            obj_type = calculatePortalTypeOfInternalPath(link, portal_url) if internal else None
            banner = dict(
                id=result.id,
                internal=internal,
                title=result.Title,
                image=obj.absolute_url() + '/thumbnail-image',
                filename=obj.image.filename,
                contentType=obj.image.contentType,
                link=link,
                type_when_follow_url=obj_type,
            )
            banners.append(banner)
        return ApiResponse(banners)
