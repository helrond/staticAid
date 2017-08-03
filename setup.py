from setuptools import setup

setup(name='static-aid',
      version='0.1',
      description='A Jekyll static site generator for archival description serialized in JSON, ' +
                  'generated via the ArchivesSpace REST API, or by other modular backends which can be added to the system.',
      author='Hillel Arnold',
      author_email='',
      license='',
      packages=['static_aid',
                ],
      scripts=[],
      entry_points={'console_scripts': [
                                        'static-aid-get-data=static_aid.getJson:main',
                                        'static-aid-build=static_aid.makePages:main',
                                        'static-aid-link-assets=static_aid.makePages:link_assets',
                                        ],
                    },
    zip_safe=False
)
