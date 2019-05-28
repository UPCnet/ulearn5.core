from z3c.form import interfaces


class ITokenInputWidget(interfaces.ITextLinesWidget):
    """Text lines widget."""


class IAjaxSelectWidget(interfaces.ITextWidget):
    """Marker interface for the Select2Widget."""


class ITagsSelectWidget(interfaces.ITextWidget):
    """Marker interface for the tags Select2Widget."""


class IFieldsetWidget(interfaces.ITextLinesWidget):
    """Fieldset widget."""


class IMaxPortraitWidget(interfaces.ITextLinesWidget):
    """Max Portrait widget."""


class ITermsWidget(interfaces.ITextLinesWidget):
    """Terms widget."""


class IPrivatePolicyWidget(interfaces.ITextLinesWidget):
    """Terms widget."""


class IVisibilityWidget(interfaces.ISingleCheckBoxWidget):
    """Visibility widget."""


class ICheckboxInfoWidget(interfaces.ICheckBoxWidget):
    """Checkbox Info widget."""
