from cStringIO import StringIO
from OFS.Image import Image
from PIL import ImageOps
from Products.CMFCore.utils import getToolByName
from Products.PlonePAS.interfaces.membership import IMembershipTool

from mrs5.max.utilities import IMAXClient
from ulearn5.theme.interfaces import IUlearn5ThemeLayer
from base5.core.adapters.portrait import IPortraitUploadAdapter
from zope.component import getUtility
from repoze.catalog.query import Eq
from souper.soup import get_soup
from souper.soup import Record
from plone import api

import logging
import PIL
from zope.interface import implements
from zope.component import adapts
from base5.core.utils import portal_url, convertSquareImage, get_safe_member_by_id
import requests
import io

logger = logging.getLogger(__name__)


class PortraitUploadAdapter(object):
    """ Default adapter for portrait custom actions """
    implements(IPortraitUploadAdapter)
    adapts(IMembershipTool, IUlearn5ThemeLayer)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, portrait, safe_id):
        if portrait and portrait.filename:
            # scaled, mimetype = scale_image(portrait, max_size=(250, 250))
            scaled, mimetype = convertSquareImage(portrait)
            if scaled:
                portrait = Image(id=safe_id, file=scaled, title='')
                membertool = getToolByName(self.context, 'portal_memberdata')
                membertool._setPortrait(portrait, safe_id)

                # Comprobamos si es la imagen por defecto o no y actualizamos el soup
                member_info = get_safe_member_by_id(safe_id)
                if member_info.get('fullname', False) \
                   and member_info.get('fullname', False) != safe_id \
                   and isinstance(portrait, Image) and portrait.size != 3566 and portrait.size != 6186:
                    portrait_user = True
                else:
                    portrait_user = False

                portal = api.portal.get()
                soup_users_portrait = get_soup('users_portrait', portal)
                exist = [r for r in soup_users_portrait.query(Eq('id_username', safe_id))]
                if exist:
                    user_record = exist[0]
                    user_record.attrs['id_username'] = safe_id
                    user_record.attrs['portrait'] = portrait_user
                else:
                    record = Record()
                    record_id = soup_users_portrait.add(record)
                    user_record = soup_users_portrait.get(record_id)
                    user_record.attrs['id_username'] = safe_id
                    user_record.attrs['portrait'] = portrait_user
                soup_users_portrait.reindex(records=[user_record])


                # Update the user's avatar on MAX
                # the next line to user's that have '-' in id
                safe_id = safe_id.replace('--', '-')
                scaled.seek(0)

                # Upload to MAX server using restricted user credentials
                maxclient, settings = getUtility(IMAXClient)()
                maxclient.setActor(settings.max_restricted_username)
                maxclient.setToken(settings.max_restricted_token)
                try:
                    maxclient.people[safe_id].avatar.post(upload_file=scaled)
                except Exception as exc:
                    logger.error(exc.message)
