from zope.interface import implements

from plone.app.contenttypes.interfaces import IFile
from plone.app.contenttypes.interfaces import IImage
from plone.app.contenttypes.content import File
from plone.app.contenttypes.content import Image

from ulearn5.core.interfaces import IAppImage
from ulearn5.core.interfaces import IAppFile


class AppFile(File):
    implements(IFile, IAppFile)


class AppImage(Image):
    implements(IImage, IAppImage)
