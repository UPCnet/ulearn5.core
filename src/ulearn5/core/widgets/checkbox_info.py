# -*- coding: utf-8 -*-

from z3c.form import interfaces
from z3c.form.browser.checkbox import CheckBoxWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile

from ulearn5.core.widgets.interfaces import ICheckboxInfoWidget

import z3c.form.browser.text
import z3c.form.interfaces
import z3c.form.widget
import zope.interface
import zope.schema.interfaces


class CheckboxInfoWidget(CheckBoxWidget):
    zope.interface.implementsOnly(ICheckboxInfoWidget)

    klass = u'checbox-info-widget'
    input_template = ViewPageTemplateFile('templates/checkbox_info_input.pt')

    def render(self):
        return self.input_template(self)


@zope.interface.implementer(zope.schema.interfaces.IBool, interfaces.IFormLayer)
@zope.interface.implementer(z3c.form.interfaces.ICheckBoxWidget)
def CheckboxInfoFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, CheckboxInfoWidget(request))
