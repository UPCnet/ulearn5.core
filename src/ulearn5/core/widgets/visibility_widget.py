# -*- coding: utf-8 -*-

from z3c.form import interfaces
from z3c.form.browser.checkbox import SingleCheckBoxWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from ulearn5.core.widgets.interfaces import IVisibilityWidget

import z3c.form.browser.text
import z3c.form.interfaces
import z3c.form.widget
import zope.interface
import zope.schema.interfaces

from zope.interface import implementer_only

@implementer_only(IVisibilityWidget)
class VisibilityWidget(SingleCheckBoxWidget):

    klass = 'visibility-widget'
    input_template = ViewPageTemplateFile('templates/visibility.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.DISPLAY_MODE:
            return self.input_template(self)
        else:
            return self.input_template(self)

    def isActive(self):
        return 'selected' in self.value


@zope.component.adapter(zope.schema.interfaces.IBool, interfaces.IFormLayer)
@zope.interface.implementer(z3c.form.interfaces.ISingleCheckBoxWidget)
def VisibilityFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, VisibilityWidget(request))
