"""
Setup script for backward compatibility.
Modern packaging uses pyproject.toml (PEP 621).
This file is maintained for tools that don't yet support pyproject.toml.
"""

from setuptools import setup

# All configuration now in pyproject.toml
# This setup.py is kept for backward compatibility only
setup()