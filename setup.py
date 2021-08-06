# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))
# Get version
version = {}
with open("minFQ/version.py") as fp:
    exec(fp.read(), version)
setup(
    name="minFQ",
    version=version["__version__"],
    description="Command line interface for uploading fastq files and monitoring minKNOW for minotour.",
    long_description=open(path.join(here, "README.rst")).read(),
    url="https://github.com/LooseLab/minotourcli",
    author="Matt Loose",
    author_email="matt.loose@nottingham.ac.uk",
    license="MIT",
    classifiers=[
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="nanopore quality control analysis",
    packages=find_packages(),
    python_requires=">=3.5",
    setup_requires=["numpy"],
    install_requires=[
        "tqdm",
        "python-dateutil",
        "requests",
        "numpy",
        "watchdog",
        "configargparse",
        "grpcio",
        "google",
        "protobuf",
        "pandas",
        "ont-fast5-api",
        "minknow-api",
        "validators",
        "grpcio-tools",
        "toml",
    ],
    package_data={"minFQ": []},
    package_dir={"minFQ": "minFQ"},
    include_package_data=True,
    entry_points={
        "console_scripts": [
            "minFQ=minFQ.minFQ:main",
        ],
    },
)
