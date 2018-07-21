from setuptools import setup, find_packages

# this is a python install script
# call it with >setup.py install
# to install all dependencies

setup(
    name='Sumo-Platooning',
    version='0.2',
    long_description="Platooning in SUMO as an extension to Simpla",
    packages=find_packages(),
    include_package_data=False,
    zip_safe=False,
    install_requires=[
        'colorama',
        'kafka-python',
        'paho-mqtt'
    ]
)