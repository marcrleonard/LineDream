#Canvas

The canvas contains all the attributes and smarts around rending the image.

When you create art, it will typically go something like this:


    from LineDream import Canvas, Line

    # create a canvas that is 300x200
    Canvas.width = 300
    Canvas.height = 200
    
    # set the background color of the canvas
    Canvas.background_color = 'green'

    # lets create a triangle
    # First, we will create a line object with one set of vertices
    l = Line([(130, 50)], close_path=True, stroke_color='yellow')

    # ... Whoops! to create a triangle, we need 3 vertices. 
    # It's ok! We can add these after the fact:
    l.add_vertex(130, 150)
    l.add_vertex(180, 100)

    #rotate this awesome triangle 120 degrees
    l.rotate(120)

    # save the final result out.
    Canvas.save("amazing_art.svg")

    #show_output    

![](../static/amazing_art.svg)