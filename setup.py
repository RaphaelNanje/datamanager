from setuptools import setup

setup(
    name='datamanager',
    version='0.1.0',
    packages=['datamanager'],
    url='https://github.com/RaphaelNanje/datamanager.git',
    license='MIT',
    author='Raphael Nanje',
    author_email='rtnanje@gmail.com',
    description='A library that makes asyncio simple',
    install_requires=[
        'diskcache',
        'easyfilemanager @ https://github.com/RaphaelNanje/easyfilemanager/'
        'archive/v3.1.2.tar.gz',
    ],
    python_requires='~=3.6',
    entry_points={
        'console_scripts': [
            'decache=easyasyncio.bin.decache:core'
                ],
        }
)
