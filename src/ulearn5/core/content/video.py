from zope.interface import implementer

from plone.app.contenttypes.interfaces import IFile
from plone.app.contenttypes.content import File

from ulearn5.core.interfaces import IVideo

@implementer(IFile, IVideo)
class Video(File):
    pass
