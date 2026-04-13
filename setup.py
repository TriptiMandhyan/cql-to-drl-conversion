from setuptools import setup, find_packages

setup(
    name="cql-to-drl-conversion",
    version="1.0.0",
    description="Convert Clinical Quality Language (CQL) to Drools Rule Language (DRL)",
    author="TriptiMandhyan",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "cql2drl=src.converter:main",
        ],
    },
    install_requires=[],
    extras_require={
        "dev": ["pytest>=7.0"],
    },
)
