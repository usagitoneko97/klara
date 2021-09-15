.. klara documentation master file, created by
   sphinx-quickstart on Tue Aug 17 17:01:14 2021.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to klara's documentation!
=================================

.. note::
    Klara is still in early experimental stage, notable missing features are loop, comprehension, module import and many more.
    See `limitation <limitation.html>`_ for full list.

Klara is a static analysis tools to automatically generate test cases, based on an SMT solver (`z3 <https://github.com/Z3Prover/z3`), with a powerful `AST <https://en.wikipedia.org/wiki/Abstract_syntax_tree>`
level inference system. Klara will take a python file as input and generate a corresponding test file in pytest format, that attempts to cover all
return values of the input file's functions. For example, the following function in file ``test.py``::

    def triangle(x: int, y: int, z: int) -> str:
        if x == y == z:
            return "Equilateral triangle"
        elif x == y or y == z or x == z:
            return "Isosceles triangle"
        else:
            return "Scalene triangle"

will generate::

    import test


    def test_triangle_0():
        assert test.triangle(0, 0, 0) == 'Equilateral triangle'
        assert test.triangle(0, 0, 1) == 'Isosceles triangle'
        assert test.triangle(2, 0, 1) == 'Scalene triangle'


The User Guide
--------------
The sections here will explain how to install and use Klara, and include steps for extending Klara.

.. toctree::
   :maxdepth: 2

   introduction.md
   quick_start.rst
   inference.rst
   extending.rst
   extending_user_type.rst
   customize_coverage_strategy.rst
   plugins.rst
   limitation.rst

The Contributor Guide
---------------------
The sections here will explain the internals workings of Klara

.. toctree::
   :maxdepth: 2

   how_does_it_works.rst
   cfg_ssa.rst

The API
-------
Documentations for modules, classes and functions.

.. toctree::
   :maxdepth: 2

   api.rst


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
