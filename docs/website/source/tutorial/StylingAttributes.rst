.. _styling-attributes:

Styling Attributes
------------------

Primitives have particular attributes that can be used to change the look of your art. If you're paying attention, you can see these attrs map directly to SVG attributes.
These attributes can be set as part of the object, or as \*\*kwargs in the constructor.

.. code-block:: python

    from LineDream import Circle, Rectangle

    #create a circle at 200, 100 with a radius of 20
    c = Circle(200,100, 20)
    # set the outer stroke to white
    c.stroke_color='white'
    # set the fill of the circle to red
    c.fill_color = 'red

    # create a rectangle, the center at (50,40)
    # it has a width of 20, and a height of 10
    # set the fill to beige as a keyword argument.
    Rectangle(50, 40, 20, 10, fill_color='beige')

fill_color
==========
Color of the inside of the shape

.. code-block:: python

    c.fill_color='red

stroke_color
============
Color of the outer stoke of the object

.. code-block:: python

    c.stroke_color='red

stroke_width
============
Width of the outer stroke. This can be `None`

.. code-block:: python

    c.stroke_width='red


close_path
==========
For Line() objects, boolean if the path should be closed. If `True`, this will draw a straight line from the first vertex, to the last.

.. code-block:: python

    c.close_path=False
