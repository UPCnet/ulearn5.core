# -*- coding: utf-8 -*-

from z3c.form import interfaces
from z3c.form.browser.checkbox import SingleCheckBoxWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from ulearn5.core.widgets.interfaces import ISingleCheckBoxNotifyEmailWidget

import z3c.form.browser.text
import z3c.form.interfaces
import z3c.form.widget
import zope.interface
import zope.schema.interfaces

class SingleCheckBoxNotifyEmailWidget(SingleCheckBoxWidget):
    zope.interface.implementsOnly(ISingleCheckBoxNotifyEmailWidget)

    klass = u'single-checkbox-notify-email-widget'

    input_template = ViewPageTemplateFile('templates/single-checkbox-notify-email-widget_input.pt')
    display_template = ViewPageTemplateFile('templates/single-checkbox-notify-email-widget_display.pt')
    hidden_template = ViewPageTemplateFile('templates/single-checkbox-notify-email-widget_hidden.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.DISPLAY_MODE:
            return self.display_template(self)
        else:
            return self.input_template(self)

@zope.component.adapter(zope.schema.interfaces.IBool, interfaces.IFormLayer)
@zope.interface.implementer(z3c.form.interfaces.IFieldWidget)
def SingleCheckBoxNotifyEmailFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, SingleCheckBoxNotifyEmailWidget(request))
