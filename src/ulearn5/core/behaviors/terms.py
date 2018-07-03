from plone.directives import form
from zope import schema
from zope.interface import alsoProvides
from zope.interface import implements

from ulearn5.core import _
from ulearn5.core.widgets.terms_widget import TermsFieldWidget


class InvalidCheckError(schema.ValidationError):
    __doc__ = ""


def isChecked(value):
    if not value:
        raise InvalidCheckError
    return True


class ITerms(form.Schema):

    form.widget(terms=TermsFieldWidget)
    terms = schema.Bool(
        title=_(u'title_terms_of_user'),
        description=_(u'description_terms_of_user'),
        constraint=isChecked
    )


alsoProvides(ITerms, form.IFormFieldProvider)


class Terms(object):
    implements(ITerms)

    def __init__(self, context):
        self.context = context
