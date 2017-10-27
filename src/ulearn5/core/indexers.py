from zope.interface import implementer
from repoze.catalog.catalog import Catalog
from repoze.catalog.indexes.field import CatalogFieldIndex
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
