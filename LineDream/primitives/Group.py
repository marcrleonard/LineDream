from .BaseShape import BaseShape
from ..enviornment.Canvas import _Canvas
import uuid

class Group(BaseShape):
    '''This will create a group. It also adds inkscape/axidraw compatible attributes
    :param label: The label of the group
    :param id: The id of the group
    '''
    def __init__(self,label=None,id=None, **kwargs):

        super().__init__(**kwargs)

        self.is_group = True

        if label == None:
            label = str(uuid.uuid4())
        self.label = label

        if id == None:
            id = label
        self.id = id

        self.items = []

    @property
    def svg_label(self):
        return f'inkscape:label="{self.label}"'

    def add_item(self, item):
        '''Add a shape to the group'''
        self.items.append(item)
        _Canvas.remove_by_id(item.id)

