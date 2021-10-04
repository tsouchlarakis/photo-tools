.. image:: graphics/photo_tools_logo.png

.. role:: raw-html(raw)
    :format: html

Utilities for reading and writing metadata from/to local photo files.

:raw-html:`<br />`

.. image:: https://img.shields.io/pypi/v/photo_tools.svg
        :target: https://pypi.python.org/pypi/photo_tools

:raw-html:`<br />`

🏁 Getting Started
==================

🧿 Prerequisites
----------------

* Python 3.X
* pip

⚙️ Installation
---------------

.. code-block:: bash

   pip install photo-tools

🌈 Releasing
------------

``photo-tools`` utilizes `versioneer <https://pypi.org/project/versioneer/>`_ for versioning. This requires the ``versioneer.py`` in the project's top-level directory, as well as some lines in the package's ``setup.cfg`` and ``__init__.py``.

1. Make your changes locally and push to ``develop`` or a different feature branch.

2. Tag the new version. This will be the version of the package once publication to PyPi is complete.

   .. code-block:: bash

      git tag {major}.{minor}.{patch}

3. Publish to PyPi.

   .. code-block:: bash

      rm -rf ./dist && python3 setup.py sdist && twine upload -r pypi dist/*

4. Install the new version of ``photo-tools``.

   .. code-block:: bash

      pip install photo-tools=={major}.{minor}.{patch}

5. Create a `pull request <https://github.com/tsouchlarakis/photo-tools/pulls>`_.


⚓️ Changelog
=============

See `changelog <CHANGELOG.rst>`_.

📜 License
==========

See `license <LICENSE>`_.


🙏 Credits
----------

This package was created with Cookiecutter_ and the `audreyr/cookiecutter-pypackage`_ project template.

.. _Cookiecutter: https://github.com/audreyr/cookiecutter
.. _`audreyr/cookiecutter-pypackage`: https://github.com/audreyr/cookiecutter-pypackage
