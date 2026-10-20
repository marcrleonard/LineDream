from .BaseShape import BaseShape
from ..environment.Canvas import _Canvas
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

    def extend(self, items):
        '''Add many shapes to the group at once. Removes them from the draw queue in a single pass,
        so it stays fast for thousands of items (add_item scans the queue once per item).'''
        items = list(items)
        self.items.extend(items)
        ids = {item.id for item in items}
        _Canvas.draw_queue = [q for q in _Canvas.draw_queue if q.id not in ids]

