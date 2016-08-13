from os import path

from setuptools import setup, find_packages

here = path.abspath(path.dirname(__file__))

setup(
    name='themis',
    version='0.1.0',
    description='A dataflow-based framework for writing robot control code',
    long_description="TODO",

    url='https://github.com/celskeggs/themis',
    author='Cel Skeggs',
    author_email='robotics-public@celskeggs.com',

    license='MIT',

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',

        'Natural Language :: English',

        'Topic :: Software Development :: Embedded Systems',
        'Topic :: Software Development :: Libraries :: Application Frameworks',

        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    keywords='robotics dataflow framework embedded',

    packages=find_packages(exclude=["wpilib"]),
    package_data={
        'themis': ['package_data.dat'],
    }
)
