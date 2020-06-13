.. _canvas:

Canvas
------

The canvas contains all the attributes and smarts around rending the image.

All art will go something like this...

.. code-block:: python

    from LineDream import Canvas, Line

    # create a canvas that is 1920x1080px
    Canvas.width = 1920
    Canvas.height = 1080
    Canvas.units = 'px'
    Canvas.background_color = 'white'

    # lets create a triangle
    l = Line([(100, 100)], close_path=True)
    l.add_vertex(100, 200)
    l.add_vertex(150, 150)

    #rotate this awesome triangle
    l.rotate(120)

    # save the final result out.
    Canvas.save('amazing_art.svg')

