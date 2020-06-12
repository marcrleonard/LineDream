.. LineDream documentation master file, created by
   sphinx-quickstart on Wed Jun 10 07:16:14 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

LineDream - a generative art library
====================================


LineDream is a generative art library for Python. It is heavily influenced by P5 and Processing. However, it takes a more object oriented approach, with less global state in regards to styling and transformations.

The current output target is SVG. As this provides a robust output set for vector graphics. There is not yet support for a draw loop - it is single frame output, but you could use a loop to simulate this. There are future plans to implement an OpenGL render window.

LineDream library was originally created to make art for a pen plotter, however, the inner object structure could be applied to many different rendering platforms.


.. include:: Installation.rst


Example
-------

See this :ref:`example`


.. include:: contents.rst


* :ref:`search`
