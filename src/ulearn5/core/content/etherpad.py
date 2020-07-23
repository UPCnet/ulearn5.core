# -*- coding: utf-8 -*-
from plone.app.contenttypes import _
from plone.app.textfield import RichText as RichTextField
from plone.app.z3cform.widget import RichTextFieldWidget
from plone.directives import form
from plone.supermodel import model
from collective import dexteritytextindexer
from z3c.form.interfaces import IAddForm, IEditForm
from plone.dexterity.content import Item
from zope.interface import implements

from plone.app.portlets.portlets import base
from z3c.form import field
from zope import schema

class IEtherpad(form.Schema):

    # Campo para que se guarde el getText que hay en etherpad 
    # para que se puedan hacer busquedas por el contenido SearchableText
    form.mode(text='hidden')
    text = schema.Text(
        title=_(u'Text Etherpad'),
        description=u'Descriptionc Etherpad',
        required=False,
        )
    dexteritytextindexer.searchable('text')
        

class Etherpad(Item):
    implements(IEtherpad)