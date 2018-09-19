# -*- coding: utf-8 -*-

from z3c.form import interfaces
from z3c.form.browser.checkbox import SingleCheckBoxWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from ulearn5.core.widgets.interfaces import IFieldsetWidget

import z3c.form.browser.text
import z3c.form.interfaces
import z3c.form.widget
import zope.interface
import zope.schema.interfaces


class VisibilityWidget(SingleCheckBoxWidget):
    zope.interface.implementsOnly(IFieldsetWidget)

    klass = u'visibility-widget'
    input_template = ViewPageTemplateFile('templates/visibility.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.DISPLAY_MODE:
            return self.input_template(self)
        else:
            return self.input_template(self)

    def isActive(self):
        return self.value == 'True'


@zope.component.adapter(zope.schema.interfaces.IField, interfaces.IFormLayer)
@zope.interface.implementer(z3c.form.interfaces.IFieldWidget)
def VisibilityFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, VisibilityWidget(request))
