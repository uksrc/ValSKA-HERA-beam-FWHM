Guide to Contributing for Developers
====================================

Thank you for your interest in contributing to ValSKA! 

We use `pre-commit <https://pre-commit.com/>`_ hooks to ensure code quality and consistency. Pre-commit hooks
automatically check your code before each commit to catch common issues early.

Installation
------------

``pre-commit`` is included in the development dependencies listed in ``pyproject.toml`` and so should have been 
installed_ along with the other dependencies in your valska environment. In order to activate ``pre-commit``, it 
must also be started at the beginning of your session on the command line:

.. _installed: readme.html#installation


.. code-block:: bash

   pre-commit install


Using Pre-commit
----------------

Once installed, the hooks will run automatically on ``git commit``. If any hook fails or modifies files, the commit will not succeed:

1. Review the changes made by the hooks
2. Stage the modified files: ``git add <modified-files>``
3. Commit again: ``git commit -m "your message"``

To skip the hooks temporarily:

.. code-block:: bash

    git commit --no-verify


To run hooks manually on specific files:

.. code-block:: bash

    pre-commit run --files <file1> <file2>


To run hooks manually on all files:

.. code-block:: bash

   pre-commit run --all-files


What the Pre-commit Hooks do
----------------------------

Our pre-commit configuration uses the formatting and linting make targets which are described here_.

.. _here: testing.html#linting-and-formatting

Pre-commit hooks are applied to:

- Python source code in ``src/`` and ``tests/``
- Notebook files in ``notebooks/``


Making Contributions
--------------------

Before Submitting a Pull Request
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Ensure all tests pass:

.. code-block:: bash

   make python-test
   make notebook-test


2. Format and lint your code:

.. code-block:: bash

   make python-format
   make python-lint
   make notebook-format
   make notebook-lint

3. Make sure pre-commit hooks pass:

.. code-block:: bash

   pre-commit run --all-files
   

Pull Request Process
~~~~~~~~~~~~~~~~~~~~

1. Create a new branch for your feature or bugfix
2. Make your changes and commit them with clear, descriptive messages
3. Push your branch to GitHub
4. Open a pull request against the main branch
5. Wait for review and address any feedback

Code Style
~~~~~~~~~~

- Python code should follow `PEP 8 <https://peps.python.org/pep-0008/>`_ guidelines (enforced by `ruff <https://docs.astral.sh/ruff/>`_)
- Line length is set to 79 characters
- Use type hints where appropriate
- Write clear docstrings for functions and classes

Jupyter Notebooks
~~~~~~~~~~~~~~~~~

- Keep notebooks focused and well-documented
- Test notebooks to ensure they run end-to-end


Thank you for contributing!
