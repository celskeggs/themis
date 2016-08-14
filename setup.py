import os
import shutil
import tempfile
import subprocess
from setuptools import setup, find_packages
from setuptools.command.build_py import build_py as base_build_py

here = os.path.abspath(os.path.dirname(__file__))


def generate_prebuilt_files(build_lib):
    print("compiling frc hal...")
    with tempfile.TemporaryDirectory() as builddir:
        source_dir = os.path.realpath(os.path.join(here, "themis-frc-hal"))
        subprocess.check_call(["cmake", source_dir], cwd=builddir)
        subprocess.check_call(["make"], cwd=builddir)
        SO_NAME = "libthemis-frc.so"
        HEADER_NAME = "themis/themis.h"

        shutil.copyfile(os.path.join(builddir, SO_NAME),
                        os.path.join(build_lib, "themis", SO_NAME))
        shutil.copyfile(os.path.join(builddir, HEADER_NAME),
                        os.path.join(build_lib, "themis", os.path.basename(HEADER_NAME)))
    print("finished compiling frc hal")


class build_py(base_build_py):  # TODO: do this the "correct way", whatever that is
    def run(self):
        super().run()
        # run after to make sure the output directory is created
        generate_prebuilt_files(self.build_lib)


setup(
    name='themis',
    version='0.1.0',
    description='A dataflow-based framework for writing robot control code',
    long_description="TODO",

    url='https://github.com/celskeggs/themis',
    author='Cel Skeggs',
    author_email='robotics-public@celskeggs.com',

    cmdclass={"build_py": build_py},

    install_requires=["setuptools"],  # for pkg_resources

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

    packages=find_packages(exclude=["themis-frc-hal"]),
    package_data={
        'themis': ['package_data.dat'],
    }
)
