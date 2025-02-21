# -*- coding: utf-8 -*-
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.namedfile.field import NamedBlobImage
from plone.supermodel import model
from ulearn5.core import _
from zope.interface import alsoProvides, provider


@provider(IFormFieldProvider)
class IThumbimage(model.Schema):
    """Add Thumbnail image to News Items for the API"""

    directives.read_permission(thumbnail_image='Zope2.View')
    thumbnail_image = NamedBlobImage(
        title=_("Thumbnail Image"),
        description="Image used in api, for App.",
        required=False,
    )

    directives.omitted('thumbnail_image')

alsoProvides(IThumbimage, IFormFieldProvider)
