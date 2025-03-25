from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from souper.interfaces import ICatalogFactory
from souper.soup import NodeAttributeIndexer
from ulearn5.core.utils import get_or_initialize_annotation
from zope.interface import implementer


@implementer(ICatalogFactory)
class MenuQuickLinksCatalogFactory(object):
    """ Les dades del menu que es mostraran segons language
        :index id_menusoup: TextIndex - id_menusoup = user_language
        :index dades: FieldIndex - Les dades del menu per aquest language
    """

    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id_menusoup')
        catalog['id_menusoup'] = CatalogTextIndex(idindexer)
        containerindexer = NodeAttributeIndexer('dades')
        catalog['dades'] = CatalogFieldIndex(containerindexer)
        return catalog

# grok.global_utility(MenuQuickLinksCatalogFactory, name="menu_soup")


@implementer(ICatalogFactory)
class HeaderSoupCatalog(object):
    """ Les dades del header que es mostraran segons language
        :index id_headersoup: TextIndex - id_headersoup = user_language
        :index dades: FieldIndex - Les dades del header per aquest language
    """

    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id_headersoup')
        catalog['id_headersoup'] = CatalogTextIndex(idindexer)
        containerindexer = NodeAttributeIndexer('dades')
        catalog['dades'] = CatalogFieldIndex(containerindexer)
        return catalog


# grok.global_utility(HeaderSoupCatalog, name="header_soup")


@implementer(ICatalogFactory)
class FooterSoupCatalog(object):
    """ Les dades del footer que es mostraran segons language
        :index id_footersoup: TextIndex - id_footersoup = user_language
        :index dades: FieldIndex - Les dades del footer per aquest language
    """

    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id_footersoup')
        catalog['id_footersoup'] = CatalogTextIndex(idindexer)
        containerindexer = NodeAttributeIndexer('dades')
        catalog['dades'] = CatalogFieldIndex(containerindexer)
        return catalog


# grok.global_utility(FooterSoupCatalog, name="footer_soup")


@implementer(ICatalogFactory)
class UserSubscribedTagsSoupCatalog(object):
    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id')
        catalog['id'] = CatalogFieldIndex(idindexer)
        hashindex = NodeAttributeIndexer('tags')
        catalog['tags'] = CatalogKeywordIndex(hashindex)
        return catalog


# grok.global_utility(UserSubscribedTagsSoupCatalog, name='user_subscribed_tags')


@implementer(ICatalogFactory)
class NotifyPopupSoupCatalog(object):
    def __call__old(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id')
        catalog['id'] = CatalogFieldIndex(idindexer)
        return catalog

    def __call__(self, context):
        notify_popup = get_or_initialize_annotation('notify_popup')
        return {
            'id': notify_popup.get('id', None),
        }



# grok.global_utility(NotifyPopupSoupCatalog, name='notify_popup')
