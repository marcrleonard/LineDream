##Primitive Attributes

All primitives have some common public attributes that are handy.


    from LineDream import Line

    # lets create a triangle
    l = Line([(10,9)], close_path=True)
    l.add_vertex(10,20)
    l.add_vertex(15,15)


###vertices


A list of all the vertices that make up the shape. NOTE: This is not available for Circle or Ellipse.
Soon, this will be migrated to a Numpy array.


    print(l.vertices)
    >>> [(10,9),(10,20),(15,15)]


###min_x

    print(l.min_x)
    >>> 10

###max_x


    print(l.max_x)
    >>> 15

###min_y

    print(l.min_y)
    >>> 9


###max_y

    print(l.max_y)
    >>> 20

###center

The center of all the points.

    print(l.center)
    >>> (12.5, 14.5)


