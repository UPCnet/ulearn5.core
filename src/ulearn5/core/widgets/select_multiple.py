# -*- encoding: utf-8 -*-
from z3c.form import interfaces
from z3c.form import widget
from z3c.form.browser.select import SelectWidget
from z3c.form.converter import BaseDataConverter
from z3c.form.interfaces import ISelectWidget
from z3c.form.widget import FieldWidget
from zope.component import adapts
from zope.formlib.interfaces import IInputWidget
from zope.formlib.widget import SimpleInputWidget
from zope.schema.interfaces import IList

import re
import zope.component
import zope.interface
import zope.schema
import zope.schema.interfaces


class FakeTerms(tuple):
    """
    """
    def getTermByToken(self, token):
        return token

    def getValue(self, value):
        return value


class ITwoLevelSelectWidget(ISelectWidget, IInputWidget):
    """Text lines widget for Gridster serialization."""


class TwoLevelWidgetConverter(BaseDataConverter):
    """Data converter for ICollection."""

    adapts(IList, ITwoLevelSelectWidget)

    def toWidgetValue(self, value):
        """Converts from field value to widget.

        :param value: Field value.
        :type value: list |tuple | set

        :returns: Items separated using separator defined on widget
        :rtype: string
        """
        if not value:
            return []
        return value

    def toFieldValue(self, value):
        """Converts from widget value to field.

        :param value: Value inserted by AjaxSelect widget.
        :type value: string

        :returns: List of items
        :rtype: list | tuple | set
        """
        if not value:
            return []
        return [tuple(re.findall(r'[^\r\n]+', selection)) for selection in value]


def expandPrefix(prefix):
        """Expand prefix string by adding a trailing period if needed.
           expandPrefix(p) should be used instead of p+'.' in most contexts.
        """
        if prefix and not prefix.endswith('.'):
            return prefix + '.'
        return prefix


class TwoLevelSelectWidget(widget.MultiWidget, SelectWidget, SimpleInputWidget):
    """
    """
    zope.interface.implementsOnly(ITwoLevelSelectWidget)
    klass = u'twolevel-widget'
    multiple = False
    size = 5

    @property
    def z3cname(self):
        return re.sub(r'(?:form.)?(?:widgets.)?(.*)', r'form.widgets.\1', self.name)

    def update(self):
        self.terms = FakeTerms()
        super(TwoLevelSelectWidget, self).update()

    def updateWidgets(self):
        pass

    def firstLevel(self):
        value = self._data if isinstance(self._data, list) else self.value
        if value:
            return value[0][0]

    def secondLevel(self):
        value = self._data if isinstance(self._data, list) else self.value
        if value and len(value[0]) == 2:
            return [val[-1] for val in value]
        else:
            return None

    def setPrefix(self, prefix):
        if prefix and not prefix.endswith("."):
            prefix += '.'
        self._prefix = prefix
        self.name = 'form.' + self.name

    @property
    def hint(self):
        return self.field.description

    # FORMLIB SHIT

    def hasInput(self):
        count = int(self.request.form.get(self.z3cname + '.count', '0'))
        return count > 0

    def getInputValue(self):
        count = int(self.request.form.get(self.z3cname + '.count', '0'))
        values = [self.request.form.get('{}.{}'.format(self.z3cname, a)) for a in range(count)]
        return [tuple(re.findall(r'[^\r\n]+', selection)) for selection in values]


@zope.component.adapter(zope.schema.interfaces.IList, interfaces.IFormLayer)
@zope.interface.implementer(interfaces.IFieldWidget)
def TwoLevelSelectFieldWidget(field, request):
    """IFieldWidget factory for SelectMultipleChoiceWidget."""
    return FieldWidget(field, TwoLevelSelectWidget(request))
