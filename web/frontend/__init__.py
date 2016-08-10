class ContentBase(object):
    """Abstract base class for everything that can be shown in the content area.
    """
    
    @property
    def node(self):
        raise NotImplementedError("must be implemented!")

    @property
    def logo(self):
        return

    @property
    def content_styles(self):
        return []

    def select_style_link(self, style):
        return ""
    
    def html(self, req):
        return ""
