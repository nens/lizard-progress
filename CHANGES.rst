Changelog of lizard-progress
===================================================


0.3 (2012-02-16)
----------------

- Added a single layer for all measurement types. Needs lizard-map 3.23
  to open popup with multiple tabs from a single layer.

- Changed measurements so that they track their originating file and a
  timestamp.

- Made it possible for a single scheduled measurement to have multiple
  measurements, because e.g. a scheduled measurement that consists of 2
  photos will have 2 uploaded files and therefore 2 measurements.

- Put timestamp in filenames of uploaded files, and if necessary a
  sequence number. Files are never overwritten, renamed or otherwise
  changed after uploading is complete. Therefore, Lizard_progress
  keeps a complete history of uploaded files.

- Made the location and structure of lizard_progress' archive
  standard, so that implementing sites don't have to bother specifying
  it. The location can be changed by setting LIZARD_PROGRESS_ROOT in
  Django settings, the structure
  (/project_slug/contractor_slug/measurement_type_slug/filename) is
  fixed.

0.2 (2012-02-15)
----------------

- Fixed bug with moving uploaded files.


0.1 (2012-02-10)
----------------

- Initial library skeleton created by nensskel.  [Remco Gerlich]

- A lot of stuff works; we can have multiple projects, multiple contractors,
  subareas, measurement types, we can schedule measurements and upload files
  that can be parsed. We can show layers and dashboard graphs and serve back the
  files, only to the right contractors or superusers. I'm marking this at 0.1 for
  no particular reason.
