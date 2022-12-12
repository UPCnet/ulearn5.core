# -*- coding: utf-8 -*-
from Products.Five.browser import BrowserView
import unicodedata


class Thumbnail(BrowserView):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        context = self.context
        if getattr(context, 'thumbnail_image', None) and context.portal_type != 'Image':
            img_data = context.thumbnail_image.open().read()
            contentType = context.thumbnail_image.contentType
            filename = unicodedata.normalize('NFKD', context.thumbnail_image.filename).encode("ascii", "ignore").decode("ascii")

            self.request.response.setHeader('content-type', contentType)
            self.request.response.setHeader(
                'content-disposition', 'inline; filename=' + str(filename.encode('utf-8')))
            self.request.response.setHeader('content-length', len(img_data))
        else:
            # Si no te la Thumb, que no peti i doni la gran...
            img_data = context.image.open().read()
            contentType = context.image.contentType
            filename = context.image.filename

            self.request.response.setHeader('content-type', contentType)
            self.request.response.setHeader(
                'content-disposition', 'inline; filename=' + str(filename.encode('utf-8')))
            self.request.response.setHeader('content-length', len(img_data))

        return img_data
