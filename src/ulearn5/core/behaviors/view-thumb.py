# -*- coding: utf-8 -*-
from PIL import Image
from Products.Five.browser import BrowserView

from io import BytesIO

import unicodedata


class Thumbnail(BrowserView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        context = self.context

        if getattr(context, 'thumbnail_image', None) and context.portal_type != 'Image':
            contentType = context.thumbnail_image.contentType
            filename = unicodedata.normalize('NFKD', context.thumbnail_image.filename).encode("ascii", "ignore").decode("ascii")
            img_open = context.thumbnail_image.open()
        else:
            # Si no te la Thumb, que no peti i doni la gran si la té
            if not context.image:
                return False

            contentType = context.image.contentType
            filename = context.image.filename
            img_open = context.image.open()

        img_data = img_open.read()

        img = Image.open(img_open)
        if contentType == 'image/png' and img.mode != "RGBA":
            img = img.convert("RGBA")

        buffer = BytesIO()
        img.save(buffer, format="PNG")

        self.request.response.setHeader('content-type', contentType)
        self.request.response.setHeader(
            'content-disposition', 'inline; filename=' + str(filename.encode('utf-8')))
        self.request.response.setHeader('content-length', len(img_data))

        return buffer.getvalue()