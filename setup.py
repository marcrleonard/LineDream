#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Minimal setup.py for backward compatibility.
All package metadata is defined in pyproject.toml.

For modern Python packaging, use:
    python -m build        # Build package
    twine upload dist/*    # Upload to PyPI
"""

from setuptools import setup

if __name__ == "__main__":
    setup()
