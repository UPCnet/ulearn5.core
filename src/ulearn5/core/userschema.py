# -*- coding: utf-8 -*-
from zope import schema
from zope.interface import Interface
from five import grok
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from souper.interfaces import ICatalogFactory
from souper.soup import NodeAttributeIndexer
from zope.interface import implementer
from plone.app.users.browser.userdatapanel import UserDataPanel

from plone.supermodel import model
from plone.z3cform.fieldsets import extensible
from zope.component import adapts
from z3c.form import field
from plone.app.users.browser.account import AccountPanelSchemaAdapter
from plone.app.users.browser.register import BaseRegistrationForm

from ulearn5.core import _
from ulearn5.core.interfaces import IUlearn5CoreLayer
from ulearn5.core.widgets.fieldset_widget import FieldsetFieldWidget


class IUlearnUserSchema(model.Schema):
    twitter_username = schema.TextLine(
        title=_(u'label_twitter', default=u'Twitter username'),
        description=_(u'help_twitter',
                      default=u'Fill in your Twitter username.'),
        required=False,
    )

    ubicacio = schema.TextLine(
        title=_(u'label_ubicacio', default=u'Ubicació'),
        description=_(u'help_ubicacio',
                      default=u'Equip, Àrea / Companyia / Departament'),
        required=False,
    )

    telefon = schema.TextLine(
        title=_(u'label_telefon', default=u'Telèfon'),
        description=_(u'help_telefon',
                      default=u'Contacte telefònic'),
        required=False,
    )

    fieldset_preferences = schema.TextLine(
        title=_(u'fieldset_preferences'),
        # description=_(u'help_fieldset_preferences'),
        required=False,
        readonly=True,
    )

    language = schema.Choice(
        title=_(u'label_language', default=u'Language'),
        description=_(u'help_language',
                      default=u"Enter your language"),
        required=False,
        vocabulary=u"plone.app.vocabularies.SupportedContentLanguages",
    )

    visible_userprofile_portlet = schema.Bool(
        title=_(u'label_userprofile', default=u'See portlet user profile'),
        description=_(u'help_userprofile', default=u'Show or hide the portlet that shows your profile picture and badges.'),
        required=False,
        default=True,
    )


class UlearnUserDataSchemaAdapter(AccountPanelSchemaAdapter):
    schema = IUlearnUserSchema

    # Aqui añadiremos los get y set de nuestro campos
    # def get_telefon(self):
    #     return self._getProperty('telefon')

    # def set_telefon(self, value):
    #     return self._setProperty('telefon', value)

    # telefon = property(get_telefon, set_telefon)


class UlearnUserDataPanelExtender(extensible.FormExtender):
    adapts(Interface, IUlearn5CoreLayer, UserDataPanel)

    def update(self):
        fields = field.Fields(IUlearnUserSchema)
        fields['fieldset_preferences'].widgetFactory = FieldsetFieldWidget
        # fields = fields.omit('telefon') # Si queremos quitar alguno de los que hemos añadido
        # self.remove('home_page') # Si queremos quitar los de la base (plone.app.users)

        self.add(fields)


class UlearnRegistrationPanelExtender(extensible.FormExtender):
    adapts(Interface, IUlearn5CoreLayer, BaseRegistrationForm)

    def update(self):
        fields = field.Fields(IUlearnUserSchema)

        self.add(fields)


@implementer(ICatalogFactory)
class UserNewsSearchSoupCatalog(object):
    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id')
        catalog['id'] = CatalogFieldIndex(idindexer)
        hashindex = NodeAttributeIndexer('searches')
        catalog['searches'] = CatalogKeywordIndex(hashindex)

        return catalog


grok.global_utility(UserNewsSearchSoupCatalog, name='user_news_searches')
