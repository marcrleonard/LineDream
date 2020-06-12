.. _transformation-methods:

Transformation Methods
----------------------

Primitives have methods to transform their vertices.

.. code-block:: python

    from LineDream import Line

    # create a triangle with the Line primitive.
    l = Line([(10,10),(10,20),(15,15)], close_path=True)

Transform
=========

The transform method will shift all vertices of a shape a given x,y amount.

.. code-block:: python

    # This will move the line 10 pixels to the right,
    # and 30 pixels down.
    l.transform(10,30)



Rotate
======

Rotate the shape a given degrees (this is in degrees... NOT radians). There is an optional `origin` \*\*kwarg. This takes a tuple of coordinates in which to rotate around.

.. code-block:: python

    # This will move rotate the shape 10 degrees.
    # Since no origin is given,
    # it will rotate around the found center of the shape.
    l.rotate(10)

    # this will rotate the shape 30 degrees,
    # using (20,50) as the origin.
    l.rotate(30, (20,50))


Scale
=====

This will scale the shape. There is an optional `origin` \*\*kwarg. This takes a tuple of coordinates in which to scale from.

.. code-block:: python

    # This will move scale the shape by 2x.
    # Since no origin is given,
    # it will scale around the found center of the shape.
    l.scale(2.0)

    # this will scale the shape 3x,
    # using (20,50) as the origin of the scale.
    l.scale(3.0, (20,50))
