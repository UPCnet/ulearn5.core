# -*- coding: utf-8 -*-
from five import grok
from plone.app.users.browser.userdatapanel import UserDataPanel
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from souper.interfaces import ICatalogFactory
from souper.soup import NodeAttributeIndexer
from zope import schema
from zope.interface import Interface
from zope.interface import implementer

from plone.app.users.browser.account import AccountPanelSchemaAdapter
from plone.app.users.browser.register import BaseRegistrationForm
from plone.supermodel import model
from plone.z3cform.fieldsets import extensible
from z3c.form import field
from zope.component import adapts

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

    # fieldset_private = schema.TextLine(
        # title=_(u'fieldset_private'),
        # description=_(u'help_fieldset_private'),
        # required=False,
        # readonly=True,
    # )


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
        # fields['fieldset_private'].widgetFactory = FieldsetFieldWidget
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
