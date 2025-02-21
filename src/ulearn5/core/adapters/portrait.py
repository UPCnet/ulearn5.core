# -*- coding: utf-8 -*-
import logging
import uuid

from base5.core.adapters.portrait import IPortraitUploadAdapter
from base5.core.utils import convertSquareImage, get_safe_member_by_id
from mrs5.max.utilities import IMAXClient
from OFS.Image import Image
from plone import api
from Products.PlonePAS.interfaces.membership import IMembershipTool
from ulearn5.core.utils import get_or_initialize_annotation
from ulearn5.theme.interfaces import IUlearn5ThemeLayer
from zope.component import adapter, getUtility
from zope.interface import implementer

logger = logging.getLogger(__name__)


@implementer(IPortraitUploadAdapter)
@adapter(IMembershipTool, IUlearn5ThemeLayer)
class PortraitUploadAdapter(object):
    """ Default adapter for portrait custom actions """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, portrait, safe_id):
        if portrait and portrait.filename:
            # scaled, mimetype = scale_image(portrait, max_size=(250, 250))
            scaled, mimetype = convertSquareImage(portrait)
            if scaled:
                portrait = Image(id=safe_id, file=scaled, title='')
                membertool = api.portal.get_tool(name='portal_memberdata')
                membertool._setPortrait(portrait, safe_id)

                # Comprobamos si es la imagen por defecto o no y actualizamos el soup
                member_info = get_safe_member_by_id(safe_id)
                if member_info.get('fullname', False) \
                   and member_info.get('fullname', False) != safe_id \
                   and isinstance(portrait, Image) and portrait.size != 3566 and portrait.size != 6186:
                    portrait_user = True
                else:
                    portrait_user = False

                soup_users_portrait = get_or_initialize_annotation('users_portrait')

                record = next((r for r in soup_users_portrait.values() if r.get('id_username') == safe_id), None)

                if record:
                    record['id_username'] = safe_id
                    record['portrait'] = portrait_user
                else:
                    unique_key = str(uuid.uuid4())
                    soup_users_portrait[unique_key] = {
                        'id_username': safe_id,
                        'portrait': portrait_user
                    }


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
