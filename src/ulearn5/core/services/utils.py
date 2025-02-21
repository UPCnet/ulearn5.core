import logging
import re

from AccessControl import getSecurityManager
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from ulearn5.core.services import MissingParameters, ObjectNotFound


def lookup_community(community_id=None):
    """ This function is used to look for a community by its ID
    (hash or gwuuid) in the DB. If we don't find it, we assume a bad path has been requested. """
    pc = api.portal.get_tool(name='portal_catalog')

    if not community_id:
        error_message = 'Community ID is missing in the request parameters.'
        logging.error(error_message)
        raise MissingParameters('Community ID not provided')

    result = pc.searchResults(community_hash=community_id)

    if not result:
        # Fallback search by gwuuid
        result = pc.searchResults(gwuuid=community_id)

    if not result:
        # Not found either by hash nor by gwuuid
        error_message = f'Community with ID {community_id} not found.'
        logging.error(error_message)
        raise ObjectNotFound(f'Community with ID {community_id} not found')

    return result[0].getObject()


def lookup_group(id):
    groups_tool = api.portal.get_tool('portal_groups')
    group = groups_tool.getGroupById(id)

    return group


def lookup_user(id, raisable=False):
    user = api.user.get(username=id)
    if not user and raisable:
        raise ObjectNotFound(f'User with ID {id} not found')
    return user


def check_include_cloudfile(obj):
    """ Should we add cloudfile? """
    sm = getSecurityManager()
    return True if sm.checkPermission(ModifyPortalContent, obj.getObject()) else False


def lookup_new(params):
    pc = api.portal.get_tool('portal_catalog')

    if not params:
        error_message = 'News Item parameters are missing in the request parameters.'
        logging.error(error_message)
        raise MissingParameters('News Item parameters are missing.')

    result = pc.searchResults(**params)

    if not result:
        return None

    return result[0].getObject()


def show_news_in_app():
    return api.portal.get_registry_record(
        name='ulearn5.core.controlpanel.IUlearnControlPanelSettings.show_news_in_app'
    )


def replace_image_path_by_url(self, msg):
    srcs = re.findall('src="([^"]+)"', msg)

    # Transform internal images
    uids = re.findall(r"resolveuid/(.*?)/@@images", msg)
    for i in range(len(uids)):
        thumb_url = api.content.get(UID=uids[i]).absolute_url() + '/thumbnail-image'
        plone_url = srcs[i]
        msg = re.sub(plone_url, thumb_url, msg)

    # Transformamos images against the site
    images = re.findall(r"/@@images/.*?\"", msg)
    for i in range(len(images)):
        msg = re.sub(images[i], '/thumbnail-image"', msg)

    return msg
