# -*- coding: utf-8 -*-
from plone.registry.interfaces import IRegistry
from z3c.form.browser.checkbox import CheckBoxWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryUtility
from zope.interface import implementer

from ulearn5.core.controlpanel import IUlearnControlPanelSettings


class TermsWidget(CheckBoxWidget):
    klass = 'terms-widget'
    input_template = ViewPageTemplateFile('templates/terms.pt')
    hidden_template = ViewPageTemplateFile('templates/terms_hidden.pt')

    def render(self):
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        if ulearn_tool.url_terms == None or ulearn_tool.url_terms == '':
            self.mode = 'hidden'
            template = self.hidden_template(self)
        elif '@@edit' in self.request.getURL():
            template = self.hidden_template(self)
        else:
            template = self.input_template(self)

        return template

    def url(self):
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        return ulearn_tool.url_terms


@implementer(IFieldWidget)
def TermsFieldWidget(field, request):
    return FieldWidget(field, TermsWidget(request))
