#!/usr/bin/env python

"""The setup script."""

import versioneer
from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [ ]

test_requirements = [ ]

setup(
    author="Andoni Sooklaris",
    author_email='andoni.sooklaris@gmail.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    description="Utilities for reading and writing metadata from/to local photo files.",
    install_requires=requirements,
    license="MIT license",
    # long_description_content_type='text/x-rst',
    # long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='photo_tools',
    name='photo_tools',
    packages=find_packages(include=['photo_tools', 'photo_tools.*']),
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/tsouchlarakis/photo_tools',
    version=versioneer.get_version(),
    cmdclass=versioneer.get_cmdclass(),
    zip_safe=False,
)
