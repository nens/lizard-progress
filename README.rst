lizard-progress
==========================================

This is a generic Lizard app for keeping track of the progress of large
measurement projects.

Split off from a project where measurements were taken of a large
number of points along waterways, consisting of depth measurements,
photos and other data.

To make this work with your site, you'll have to implement all of the code
specific to your project:

- Custom import scripts that setup the locations in your project, etc.

- Parsers for uploaded files of each type (it's a very new tradition
  to put these in parsers.py). Parsers are responsible for putting the
  data they read into the database and return a SuccessfulParserResult
  or UnSuccessfulParserResult object. Lizard-progress will make sure
  that this happens in the context of a database transaction, and will
  roll back everything if the parse was unsuccessful.

- HTML and Image handlers for showing popups and collage pages of your
  data.

- A "Specifics" object that points to parsers and handlers, it should
  inherit from lizard_progress.specifics.GenericSpecifics (and probably
  be placed in progress.py in your project).

- Setup.py in your project should have entry points that allow lizard-progress
  to find your Specifics objects; e.g. for HDSR:

      entry_points={
          'console_scripts': [],
          'lizard_progress.project_specifics': [
            'dwarsprofielen = hdsr.progress:Dwarsprofielen',
            'peilschalen = hdsr.progress:Peilschalen',],
      }

- Nginx.conf.in in your project's etc directory should have a few
  lines that allow lizard-progress to serve back uploaded files (like
  photos that you want to show in popups):

    location /protected/ {
       internal;
       alias ${buildout:directory}/var/lizard_progress/ ;
    }

- Uploaded files are placed in BUILDOUT_DIR+"/var/" by default, in a
  project_slug/contractor_slug/measurement_type_slug/filename
  structure.

The HDSR site is currently the only site that uses this, so look there
for examples.

Design musings
--------------

Since such projects are inherently very different from each other, it
remains to be seen how much can be made generic. At this point we have
one project more or less working (it will be ported to this library)
and one project for the same customer starting up. As we use this
library for more projects it will probably evolve a lot.

Things that might be generic:

- A project has a table of locations with an ID and a geometry, often
  along with other fields

- The locations are possibly split up in subareas

- At each location, measurements of several different types are made.

- These are entered into the system by uploading files. One file may
  contain measurements of one or more points, and of one or more types
  of data for each point.

- Files may need strict correctness checks before they are accepted.

- Uploaded files should be kept around.

- There may be more than one company uploading results (for control),
  and they should not see each other's data

- So for each location X, we need to keep track of whether company Y will
  make measurements for it

- We need to know for each point and each company whether if there is
  no data, incomplete data or complete data

- We want to be able to show graphs, photos etc of each measurement at
  a point at one page, although the details of how to do this may be
  left to the implementing Lizard site

- Similarly the presentation of data and actually anything that needs
  knowledge of what the data looks like can be left to the site

- We need nice pie charts of the project's progress, because that's
  what the project is called.
