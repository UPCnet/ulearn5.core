# -*- coding: utf-8 -*-

import z3c.form.browser.text
import z3c.form.interfaces
import z3c.form.widget
from ulearn5.core.widgets.interfaces import IFieldsetWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import implementer, implementer_only


@implementer_only(IFieldsetWidget)
class FieldsetWidget(z3c.form.browser.text.TextWidget):

    klass = 'fieldset-widget'
    input_template = ViewPageTemplateFile('templates/fieldset.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.DISPLAY_MODE:
            return self.input_template(self)
        else:
            return self.input_template(self)
        


@implementer(z3c.form.interfaces.IFieldWidget)
def FieldsetFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, FieldsetWidget(request))

@implementer_only(IFieldsetWidget)
class H3FieldsetWidget(z3c.form.browser.text.TextWidget):

    klass = 'fieldset-widget'
    input_template = ViewPageTemplateFile('templates/h3_fieldset.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.DISPLAY_MODE:
            return self.input_template(self)
        else:
            return self.input_template(self)


@implementer(z3c.form.interfaces.IFieldWidget)
def H3FieldsetFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, H3FieldsetWidget(request))

@implementer_only(IFieldsetWidget)
class H4FieldsetWidget(z3c.form.browser.text.TextWidget):

    klass = 'fieldset-widget'
    input_template = ViewPageTemplateFile('templates/h4_fieldset.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.DISPLAY_MODE:
            return self.input_template(self)
        else:
            return self.input_template(self)


@implementer(z3c.form.interfaces.IFieldWidget)
def H4FieldsetFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, H4FieldsetWidget(request))


@implementer_only(IFieldsetWidget)
class H5FieldsetWidget(z3c.form.browser.text.TextWidget):

    klass = 'fieldset-widget'
    input_template = ViewPageTemplateFile('templates/h5_fieldset.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.DISPLAY_MODE:
            return self.input_template(self)
        else:
            return self.input_template(self)


@implementer(z3c.form.interfaces.IFieldWidget)
def H5FieldsetFieldWidget(field, request):
    return z3c.form.widget.FieldWidget(field, H5FieldsetWidget(request))
