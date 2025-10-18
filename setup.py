from setuptools import setup, find_packages

setup(
    name="pkms",
    version="0.1.0",
    description="Personal Knowledge Management System - CLI for Obsidian vault management",
    author="gstvolvr",
    packages=find_packages(),
    install_requires=[
        "click>=8.0.0",
        "python-frontmatter",
        "osxphotos",
        "geopy",
        "requests",
        "numpy",
        "tqdm",
        "PyYAML",
    ],
    entry_points={
        "console_scripts": [
            "pkms=pkms.cli:cli",
        ],
    },
    python_requires=">=3.8",
)
