# -*- coding: utf-8 -*-
from plone.autoform import directives
from plone.autoform.interfaces import IFormFieldProvider
from plone.directives import form
from plone.namedfile import field as namedfile
from plone.supermodel import model
from zope.interface import alsoProvides
from zope.interface import provider

from ulearn5.core import _


@provider(IFormFieldProvider)
class IThumbimage(model.Schema):
    """Add Thumbnail image to News Items for the API
    """

    directives.read_permission(thumbnail_image='Zope2.View')
    thumbnail_image = namedfile.NamedBlobImage(
        title=_("Thumbnail Image"),
        description="Image used in api, for App.",
        required=False,
    )

    # hide the field
    form.omitted('thumbnail_image')


alsoProvides(IThumbimage, form.IFormFieldProvider)
