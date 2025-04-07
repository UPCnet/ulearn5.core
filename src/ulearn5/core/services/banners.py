# -*- coding: utf-8 -*-
import logging

from plone import api
from plone.registry.interfaces import IRegistry
from plone.restapi.services import Service
from ulearn5.core.services import UnknownEndpoint, check_methods, check_roles
from zope.component import queryUtility

from ulearn5.core.controlpanel import IUlearnControlPanelSettings
from ulearn5.core.utils import calculatePortalTypeOfInternalPath


logger = logging.getLogger(__name__)


class Banners(Service):
    """
    - Endpoint: @api/banners
    - Method: GET
        Returns a dict containing information about the banners.
    - Subpaths allowed: NO
    """

    def __init__(self, context, request, **kwargs):
        self.context = context
        self.request = request

    def handle_subpath(self, subpath):
        """ Function used to spread the request to the corresponding subpath """
        if subpath:
            return UnknownEndpoint(f'Unknown sub-endpoint: {"/".join(subpath)}')

        return self.reply()

    @check_roles(roles=['Manager', 'Member', 'Api'])
    @check_methods(methods=['GET'])
    def reply(self):
        banners = []
        results = self.find_banner_results()
        portal_url = self.get_portal_url()

        for result in results:
            banner = self.get_banner_from_result(result, portal_url)
            if banner:
                banners.append(banner)

        return {"data": banners, "code": 200}

    def find_banner_results(self):
        """ Find all banners """
        return api.content.find(
            portal_type="ulearn.banner",
            path='/'.join(api.portal.get().getPhysicalPath()) + "/gestion/banners",
            review_state=['intranet'],
            sort_on='getObjPositionInParent',
        )

    def get_portal_url(self):
        """ Get the portal URL """
        portal = api.portal.get()
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        if ulearn_tool.url_site == None or ulearn_tool.url_site == '':
            return portal.absolute_url()

        return ulearn_tool.url_site

    def get_banner_from_result(self, result, portal_url):
        """ Build the banner information from the result """
        obj = result.getObject()
        obj_url = obj.url

        if '/search' in obj_url:
            return None

        if obj_url.startswith('/'):
            obj_url = portal_url + obj_url

        internal = True if obj_url.startswith(portal_url) else False

        link = obj_url.replace('#', '') if internal else obj_url
        obj_type = calculatePortalTypeOfInternalPath(
            link, portal_url) if internal else None
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
        return banner
