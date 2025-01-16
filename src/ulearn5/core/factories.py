import transaction
from _thread import allocate_lock

from plone import api
from zope.component import getMultiAdapter
from zope.component import adapts
from zope.container.interfaces import INameChooser
from zope.interface import implements

from Products.CMFCore.interfaces._content import IFolderish

try:
    from plone.namedfile.file import NamedBlobImage
    from plone.namedfile.file import NamedBlobFile
except ImportError:
    # only for dext
    pass

from ulearn5.core.interfaces import IDXFileFactory

upload_lock = allocate_lock()


class DXFileFactory(object):
    """ Ripped out from above """
    implements(IDXFileFactory)
    adapts(IFolderish)

    def __init__(self, context):
        self.context = context

    def __call__(self, name, content_type, data, title, request):
        # contextual import to prevent ImportError
        from plone.dexterity.utils import createContentInContainer

        ctr = api.portal.get_tool(name='content_type_registry')
        type_ = ctr.findTypeName(name.lower(), '', '') or 'File'

        name = name.decode('utf8')
        title = title.decode('utf8')

        chooser = INameChooser(self.context)

        # otherwise I get ZPublisher.Conflict ConflictErrors
        # when uploading multiple files
        upload_lock.acquire()

        def trim_title(title):
            pview = getMultiAdapter((self.context, request), name='plone')
            return pview.cropText(title, 40)

        if title:
            newid = chooser.chooseName(title, self.context.aq_parent)
        else:
            newid = chooser.chooseName(name, self.context.aq_parent)

        try:
            transaction.begin()
            # Try to determine which kind of NamedBlob we need
            # This will suffice for standard p.a.contenttypes File/Image
            # and any other custom type that would have 'File' or 'Image' in
            # its type name
            if 'File' in type_:
                file = NamedBlobFile(data=data.read(),
                                     filename=str(data.filename),
                                     contentType=content_type)
                obj = createContentInContainer(self.context,
                                               'AppFile',
                                               id=newid,
                                               title=trim_title(title),
                                               description=title,
                                               file=file,
                                               checkConstraints=False)
            elif 'Image' in type_:
                image = NamedBlobImage(data=data.read(),
                                       filename=str(data.filename),
                                       contentType=content_type)

                obj = createContentInContainer(self.context,
                                               'AppImage',
                                               id=newid,
                                               title=trim_title(title),
                                               description=title,
                                               image=image,
                                               checkConstraints=False)

            # obj.title = name
            obj.reindexObject()
            transaction.commit()

        finally:
            upload_lock.release()

        return obj
