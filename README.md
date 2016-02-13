# Project Name

A [Jekyll](http://jekyllrb.com/) static site generator for archival description serialized in JSON, generated via the [ArchivesSpace](http://archivesspace.org) REST API.

## Requirements

*   Python (tested on v2.7)
*   Python modules?
*   Jekyll (to build the site)
*   Grunt (for running build and deployment tasks)
*   An ArchivesSpace instance

## Installation

### Create Configuration file
Run `utilities/setup.py` to create a configuration file which will allow you to fetch and update data from ArchivesSpace.

### Build and Preview Site
Run `grunt build` to create the HTML for your site. Depending on the size of your ArchivesSpace installation, this could take quite a while. This will do the following:

1.  Fetch JSON for resource records, resource record trees and archival objects from ArchivesSpace using `utilities\getJson.py`.
2.  Run `utilities\makePages.py` to generate placeholder pages for each collection.
3.  Run `jekyll serve` to create the static HTML site and start a local server.

After this process is complete, you should be able to access the site by opening a browser and pointing it to `http://localhost:4000`.

## Usage

### Clean Build
By default, the build process will only fetch JSON updated since the last time `utilities\getJson.py` completed successfully. At any point, you can run `grunt build:clean` to wipe out the existing data and build the site from scratch.

### Github Pages
Github Pages support Jekyll sites, so a quick way to make your description publicly accessible is to push to a `gh-pages` branch in a Github repository. See the [Github Pages](https://pages.github.com/) documentation for more information.

## Contributing

Pull requests accepted! Feel free to file issues on this repository as well.

## Authors

Hillel Arnold

## License

staticAid is released under the MIT License. See `LICENSE.md` for more information.
