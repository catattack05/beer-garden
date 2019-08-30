import re

from setuptools import setup, find_packages

with open("README.rst") as readme_file:
    readme = readme_file.read()


def find_version(version_file):
    version_line = open(version_file, "rt").read()
    match_object = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_line, re.M)

    if not match_object:
        raise RuntimeError("Unable to find version string in %s" % version_file)

    return match_object.group(1)


setup(
    name="bartender",
    version=find_version("bartender/_version.py"),
    description="Beergarden Backend",
    long_description=readme,
    author="The beer-garden Team",
    author_email="bartender@beer-garden.io",
    url="https://beer-garden.io",
    packages=(find_packages(exclude=["test", "test.*"])),
    license="MIT",
    keywords="bartender beer beer-garden beergarden",
    install_requires=[
        "apispec==0.38.0",
        "apscheduler==3.6.0",
        "brewtils>=3.0.0a1",
        "mongoengine<0.16",
        "passlib<1.8",
        "prometheus-client==0.7.1",
        "pyrabbit2==1.0.7",
        "pytz<2019",
        "ruamel.yaml<0.16",
        "tornado==6.0.3",
        "yapconf>=0.3.3",
    ],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    entry_points={
        "console_scripts": [
            "generate_bartender_config=bartender.__main__:generate_config",
            "migrate_bartender_config=bartender.__main__:migrate_config",
            "generate_bartender_log_config=bartender.__main__:generate_logging_config",
            "bartender=bartender.__main__:main",
        ]
    },
)
