from setuptools import setup, find_packages

setup(
    name="waterfall-py",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas>=1.4.0",
        "numpy>=1.21.0",
    ],
)
