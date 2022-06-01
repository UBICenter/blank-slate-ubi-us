from setuptools import setup

setup(
    name="blank_slate_ubi_us",
    version="0.0.1",
    packages=["blank_slate_ubi_us"],
    install_requires=[
        "pandas",
        "numpy",
        "scipy",
        "openfisca-us",
        "plotly",
        "ubicenter",
        "black",
        "argparse",
    ],
)
