# -*- coding: utf-8 -*-
from plone.registry.interfaces import IRegistry
from z3c.form.browser.checkbox import CheckBoxWidget
from z3c.form.interfaces import IFieldWidget
from z3c.form.widget import FieldWidget
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import queryUtility
from zope.interface import implementer

from ulearn5.core.controlpanel import IUlearnControlPanelSettings


class PrivatePolicyWidget(CheckBoxWidget):
    klass = 'private_policy-widget'
    input_template = ViewPageTemplateFile('templates/private_policy.pt')

    def render(self):
        return self.input_template(self)

    def url(self):
        registry = queryUtility(IRegistry)
        ulearn_tool = registry.forInterface(IUlearnControlPanelSettings)
        return ulearn_tool.url_private_policy


@implementer(IFieldWidget)
def PrivatePolicyFieldWidget(field, request):
    return FieldWidget(field, PrivatePolicyWidget(request))
