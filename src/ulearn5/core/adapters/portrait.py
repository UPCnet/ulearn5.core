from cStringIO import StringIO
from OFS.Image import Image
from PIL import ImageOps
from five import grok
from Products.CMFCore.utils import getToolByName
from Products.PlonePAS.interfaces.membership import IMembershipTool

from mrs5.max.utilities import IMAXClient
from ulearn5.theme.interfaces import IUlearn5ThemeLayer
from base5.core.adapters.portrait import IPortraitUploadAdapter
from zope.component import getUtility
from zope.interface import Interface

import logging
import PIL

logger = logging.getLogger(__name__)


@grok.implementer(IPortraitUploadAdapter)
@grok.adapter(IMembershipTool, IUlearn5ThemeLayer)
class PortraitUploadAdapter(object):
    """ Default adapter for portrait custom actions """
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self, portrait, safe_id):
        if portrait and portrait.filename:
            # scaled, mimetype = scale_image(portrait, max_size=(250, 250))
            scaled, mimetype = convertSquareImage(portrait)
            portrait = Image(id=safe_id, file=scaled, title='')
            membertool = getToolByName(self.context, 'portal_memberdata')
            membertool._setPortrait(portrait, safe_id)

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


def convertSquareImage(image_file):
    CONVERT_SIZE = (250, 250)
    image = PIL.Image.open(image_file)
    format = image.format
    mimetype = 'image/%s' % format.lower()

    # Old way
    # if image.size[0] > 250 or image.size[1] > 250:
    #     image.thumbnail((250, 9800), PIL.Image.ANTIALIAS)
    #     image = image.transform((250, 250), PILImage.EXTENT, (0, 0, 250, 250), PILImage.BICUBIC)

    result = ImageOps.fit(image, CONVERT_SIZE, method=PIL.Image.ANTIALIAS, centering=(0.5, 0.5))
    new_file = StringIO()
    result.save(new_file, format, quality=88)
    new_file.seek(0)

    return new_file, mimetype
