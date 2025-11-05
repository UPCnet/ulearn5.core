import logging
import re

from Acquisition import aq_inner
from AccessControl import getSecurityManager
from plone import api
from Products.CMFCore.permissions import ModifyPortalContent
from ulearn5.core.services import MissingParameters, ObjectNotFound
from ulearn5.core.content.community import ICommunity
import logging

logger = logging.getLogger(__name__)


def lookup_community(community_id=None):
    """ This function is used to look for a community by its ID
    (hash or gwuuid) in the DB. If we don't find it, we assume a bad path has been requested. """
    pc = api.portal.get_tool(name='portal_catalog')

    if not community_id:
        error_message = 'Community ID is missing in the request parameters.'
        logging.error(error_message)
        raise MissingParameters('Community ID not provided')

    result = pc.unrestrictedSearchResults(portal_type='ulearn.community',
                                          id=community_id)

    if not result:
        # Fallback search by gwuuid
        result = pc.searchResults(gwuuid=community_id)

    if result:
        return result[0].getObject()
    else:
        return result



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


def replace_image_path_by_url(msg):
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


def urlBelongsToCommunity(url, portal_url):
    tree_site = api.portal.get()
    partial_path = url.split(portal_url)[1]
    partial_path.replace('#', '')  # Sanitize if necessary
    if partial_path.endswith('/view/'):
        partial_path = partial_path.split('/view/')[0]
    elif partial_path.endswith('/view'):
        partial_path = partial_path.split('/view')[0]

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