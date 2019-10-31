# -*- coding: utf-8 -*-
from plone import api
from plone.formwidget.namedfile.interfaces import INamedImageWidget
from plone.formwidget.namedfile.widget import NamedFileWidget
from plone.namedfile.interfaces import INamedImage
from plone.namedfile.interfaces import INamedImageField
from z3c.form.interfaces import IFieldWidget
from z3c.form.interfaces import IFormLayer
from z3c.form.widget import FieldWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import adapter
from zope.interface import implementer
from zope.interface import implementer_only

import z3c.form.browser.text
import z3c.form.interfaces
import z3c.form.widget


@implementer_only(INamedImageWidget)
class MaxPortraitWidget(NamedFileWidget):
    """A widget for a named file object
    """

    input_template = ViewPageTemplateFile('templates/max_portrait_input.pt')
    display_template = ViewPageTemplateFile('templates/max_portrait_display.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.DISPLAY_MODE:
            return self.display_template(self)
        else:
            return self.input_template(self)

    klass = u'max-portrait-widget'

    @property
    def width(self):
        if INamedImage.providedBy(self.value):
            return self.value._width
        else:
            return None

    @property
    def height(self):
        if INamedImage.providedBy(self.value):
            return self.value._height
        else:
            return None

    @property
    def alt(self):
        return self.title

    @property
    def portal_url(self):
        return api.portal.get().absolute_url()

    @property
    def username(self):
        if 'userid' in self.request.keys():
            return self.request['userid']
        elif self.context.portal_type == 'switchmed.profile':
            return self.context.id
        else:
            return api.user.get_current().Title()

    def is_admin_user(self):
        if api.user.get_current().id == 'admin':
            return True
        else:
            return False


@implementer(IFieldWidget)
@adapter(INamedImageField, IFormLayer)
def MaxPortraitFieldWidget(field, request):
    return FieldWidget(field, MaxPortraitWidget(request))
