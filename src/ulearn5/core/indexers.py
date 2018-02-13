from zope.interface import implementer
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
from repoze.catalog.indexes.keyword import CatalogKeywordIndex
from repoze.catalog.indexes.text import CatalogTextIndex
from souper.interfaces import ICatalogFactory
from souper.soup import NodeAttributeIndexer
from five import grok


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

grok.global_utility(MenuQuickLinksCatalogFactory, name="menu_soup")


@implementer(ICatalogFactory)
class UserSubscribedTagsSoupCatalog(object):
    def __call__(self, context):
        catalog = Catalog()
        idindexer = NodeAttributeIndexer('id')
        catalog['id'] = CatalogFieldIndex(idindexer)
        hashindex = NodeAttributeIndexer('tags')
        catalog['tags'] = CatalogKeywordIndex(hashindex)

        return catalog

grok.global_utility(UserSubscribedTagsSoupCatalog, name='user_subscribed_tags')
