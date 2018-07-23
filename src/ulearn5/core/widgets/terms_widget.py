# -*- coding: utf-8 -*-
from plone.registry.interfaces import IRegistry
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryUtility
from zope.interface import implementer

from ulearn5.core.controlpanel import IUlearnControlPanelSettings

import z3c.form.interfaces
import z3c.form.widget


class TermsWidget(z3c.form.browser.checkbox.CheckBoxWidget):
    klass = u'terms-widget'
    input_template = ViewPageTemplateFile('templates/terms.pt')
    hidden_template = ViewPageTemplateFile('templates/terms_hidden.pt')

    def render(self):
        if self.mode == z3c.form.interfaces.INPUT_MODE:
            return self.input_template(self)
        else:
            return self.hidden_template(self)

    def url(self):
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        return ulearn_tool.url_terms


@implementer(IFieldWidget)
def TermsFieldWidget(field, request):
    return FieldWidget(field, TermsWidget(request))
