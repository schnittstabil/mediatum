class ContentBase(object):
    """Abstract base class for everything that can be shown in the content area.
    """
    
    def select_style_link(self):
        return ""
    
    @property
    def node(self):
        raise NotImplementedError("must be implemented!")
