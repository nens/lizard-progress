lizard-progress
==========================================

This is a generic Lizard app for keeping track of the progress of large
measurement projects.

Split off from a project where measurements were taken of a large
number of points along waterways, consisting of depth measurements,
photos and other data.

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

