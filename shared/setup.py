"""
Setup script for timetable_shared package.
"""
from setuptools import setup, find_packages

setup(
    name="timetable-shared",
    version="1.0.0",
    description="Shared code for timetable distributed system",
    packages=find_packages(),
    install_requires=[
        "sqlalchemy>=2.0.0",
        "psycopg2-binary>=2.9.0",
    ],
)
