from zope.interface import implements

from plone.app.contenttypes.interfaces import IFile
from plone.app.contenttypes.content import File

from ulearn5.core.interfaces import IVideo


class Video(File):
    implements(IFile, IVideo)
