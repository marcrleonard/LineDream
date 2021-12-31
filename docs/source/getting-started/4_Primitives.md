##Primitives

This is the list of primitive object shapes and types that LineDream provides. These are the building blocks of all the art you will create.

All primitive objects have access to:

* [Primitive Attributes](#PrimitivesAttributes) - Attrs that describe the shape
* [Styling Attributes](#StylingAttributes) - Attrs that change the way the shape looks
* [Transformation Methods](#TransformationMethods) - Methods that move, rotate, and scale the shapes


###Line

A line, simply put, is multiple sets of coordinates which when rendered create line segments. A Line can be two sets of coordinates (making one segment), or many sets of coordinates.


    from LineDream import Line
    # this a line object with no segments defined.
    # This will not render anything.
    l = Line()
    # ... now lets add two vertex points.
    l.add_vertex(10,60)
    l.add_vertex(20,70)
    # ... We've added two vertex's to our Line!

###Circle


    from LineDream import Circle

    # Create a Circle at (30,20)
    # It's radius is 10
    Circle(30,20, 10)

###Ellipse


    from LineDream import Ellipse

    # Create an Ellipse at (30,20)
    # It's width is 10
    # It's Height is 15
    Ellipse(30,20, 10, 15)

###Square


    from LineDream import Square

    # Create a square with it's center at (40,50)
    # It's width and height are 10
    Square(40, 50, 10)


###Rectangle


    from LineDream import Rectangle

    # Create a rectangle with it's center at (40,50)
    # It's width is 5
    # It's height is 20
    Rectangle(40, 50, 5, 20)

###TextLines (experimental)


This is an experimental feature. Currently, it (sloppily) uses Herhsey Text.
It has been hacked out of the Inkscape extension.

    from LineDream import TextLines

    # Create a path that says 'LineDreamIsAwesome'
    TextLines('LineDreamIsAwesome', kerning=5)

###LineGroup (experimental)

Coming soon...