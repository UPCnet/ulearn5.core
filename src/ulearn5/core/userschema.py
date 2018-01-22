# -*- coding: utf-8 -*-
from zope import schema
from zope.interface import Interface
from zope.interface import implements
from plone.namedfile.field import NamedBlobImage
# from mrs.max.userdataschema import IEnhancedUserDataSchema
from mrs5.max.userdataschema import EnhancedUserDataPanelAdapter
# from mrs.max.userdataschema import UserDataSchemaProvider

# from plone.app.users.browser.formlib import FileUpload
# from plone.app.users.userdataschema import IUserDataSchemaProvider
from plone.app.users.schema import ICombinedRegisterSchema
from plone.app.users.schema import checkEmailAddress

from zope.interface import alsoProvides
from zope.component import getUtility
from mrs5.max.utilities import IMAXClient
from Products.CMFCore.utils import getToolByName
from ulearn5.core.adapters.portrait import convertSquareImage
import urllib
from OFS.Image import Image

from ulearn5.core import _

from five import grok

from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from souper.interfaces import ICatalogFactory
from souper.soup import NodeAttributeIndexer
from zope.interface import implementer


class IUlearnUserSchema(Interface):
    """ Redefinition of all the fields because of the ordering """

    fullname = schema.TextLine(
        title=_(u'label_full_name', default=u'Full Name'),
        description=_(u'help_full_name_creation',
                      default=u'Enter full name, e.g. John Smith.'),
        required=True)

    email = schema.ASCIILine(
        title=_(u'label_email', default=u'E-mail'),
        description=u'',
        required=True,
        constraint=checkEmailAddress)

    home_page = schema.TextLine(
        title=_(u'label_homepage', default=u'Home page'),
        description=_(u'help_homepage',
                      default=u'The URL for your external home page, '
                      'if you have one.'),
        required=False)

    description = schema.Text(
        title=_(u'label_biography', default=u'Biography'),
        description=_(u'help_biography',
                      default=u'A short overview of who you are and what you '
                      'do. Will be displayed on your author page, linked '
                      'from the items you create.'),
        required=False)

    location = schema.TextLine(
        title=_(u'label_location', default=u'Location'),
        description=_(u'help_location',
                      default=u'Your location - either city and '
                      'country - or in a company setting, where '
                      'your office is located.'),
        required=False)

    portrait = NamedBlobImage(
        title=_(u'label_portrait', default=u'Portrait'),
        description=_(
            u'help_portrait',
            default=u'To add or change the portrait: click the "Browse" '
                    u'button; select a picture of yourself. Recommended '
                    u'image size is 75 pixels wide by 100 pixels tall.'
        ),
        required=False)

    pdelete = schema.Bool(
        title=_(u'label_delete_portrait', default=u'Delete Portrait'),
        description=u'',
        required=False)

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

    language = schema.Choice(
        title=_(u'label_language', default=u'Language'),
        description=_(u'help_language',
                      default=u"Enter your language"),
        required=False,
        vocabulary=u"plone.app.vocabularies.SupportedContentLanguages",
    )


class UlearnUserSchema(object):
    implements(ICombinedRegisterSchema)

    def getSchema(self):
        """
        """
        return IUlearnUserSchema


class ULearnUserDataPanelAdapter(EnhancedUserDataPanelAdapter):

    def __init__(self, context):
        """ Load MAX avatar in portrait.

        """
        super(EnhancedUserDataPanelAdapter, self).__init__(context)

        try:
            from plone.protect.interfaces import IDisableCSRFProtection
            alsoProvides(self.request, IDisableCSRFProtection)
        except:
            pass

        maxclient, settings = getUtility(IMAXClient)()
        foto = maxclient.people[self.context.id].avatar
        imageUrl = foto.uri

        portrait = urllib.urlretrieve(imageUrl)

        scaled, mimetype = convertSquareImage(portrait[0])
        portrait = Image(id=self.context.id, file=scaled, title='')

        membertool = getToolByName(self.context, 'portal_memberdata')
        membertool._setPortrait(portrait, self.context.id)
        import transaction
        transaction.commit()

    def get_ubicacio(self):
        return self._getProperty('ubicacio')

    def set_ubicacio(self, value):
        return self.context.setMemberProperties({'ubicacio': value})
    ubicacio = property(get_ubicacio, set_ubicacio)

    def get_telefon(self):
        return self._getProperty('telefon')

    def set_telefon(self, value):
        return self.context.setMemberProperties({'telefon': value})
    telefon = property(get_telefon, set_telefon)

    def get_language(self):
        return self._getProperty('language')

    def set_language(self, value):
        return self.context.setMemberProperties({'language': value})

    language = property(get_language, set_language)


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
