.. _primitive-attributes:

Primitive Attributes
---------------------

All primitives have some common public attributes that are handy.

.. code-block:: python

    from LineDream import Line

    # lets create a triangle
    l = Line([(10,10)], close_path=True)
    l.add_vertex(10,20)
    l.add_vertex(15,15)


vertices
=========

A list of all the vertices that make up the shape. NOTE: This is not available for Circle or Ellipse.
Soon, this will be migrated to a Numpy array.

.. code-block:: python

   print(l.vertices)
   >>> [(10,9),(10,20),(15,15)]


min_x
=====

.. code-block:: python

   print(l.min_x)
   >>> 10

max_x
=====

.. code-block:: python

   print(l.max_x)
   >>> 15

min_y
=====

.. code-block:: python

   print(l.min_y)
   >>> 9


max_y
=====

.. code-block:: python

   print(l.max_y)
   >>> 20

center
======

The center of all the points.

.. code-block:: python

   print(l.center)
   >>> (12.5, 14.5)


