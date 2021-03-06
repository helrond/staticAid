from setuptools import setup

setup(
    name='static-aid',
    version='0.1',
    description='A Jekyll static site generator for archival description serialized in JSON, generated via the ArchivesSpace REST API, or by other modular backends which can be added to the system.',
    author='Hillel Arnold',
    author_email='',
    license='MIT',
    packages=['static_aid'],
    scripts=[],
    entry_points={
        'console_scripts': [
            'static-aid-get-data=static_aid.get_json:main',
            'static-aid-make-pages=static_aid.make_pages:main',
        ],
    },
    zip_safe=False
)
