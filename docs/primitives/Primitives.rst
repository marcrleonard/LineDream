Primitives
----------
This is the list of primitive object shapes and types that LineDream provides. These are the building blocks of all the art you will create.

All primitives* objects have access to:

* Styling attributes :ref:`styling-attributes`
* Tranformation methods


*There are a few minor exceptions

Line
====
A line, simply put, is multiple sets of coordinates which when rendered create line segments. A Line can be two sets of coordinates (making one segment), or many sets of coordinates.

.. code-block:: python

    from LineDream import Line
    # this a line object with no segments defined.
    # This will not render anything.
    l = Line()
    # ... now lets add two vertex points.
    l.add_vertex(10,60)
    l.add_vertex(20,70)
    # ... We've added two vertex's to our Line!