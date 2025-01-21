from zope.interface import implementer

from plone.app.contenttypes.interfaces import IFile
from plone.app.contenttypes.interfaces import IImage
from plone.app.contenttypes.content import File
from plone.app.contenttypes.content import Image

from ulearn5.core.interfaces import IAppImage
from ulearn5.core.interfaces import IAppFile

@implementer(IFile, IAppFile)
class AppFile(File):
    pass

@implementer(IImage, IAppImage)
class AppImage(Image):
    pass
