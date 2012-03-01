Changelog of lizard-progress
===================================================


0.6 (unreleased)
----------------

- Removed obsolete 'global_icon_complete' of measurement type.

- Made using OO parsers mandatory, removed support for functions.

- Further refactored upload view.

0.5 (2012-02-17)
----------------

- Introduced a parser class, making parsing more OO. The main reason
  to do it was separating error messages from the code but still keeping
  them together in the same class, but the end result should lead to less
  code anyway.

- We now show line numbers in error messages if using the OO parsers.


0.4 (2012-02-17)
----------------

- More measurements per scheduled measurement.

- Parsers now receive file objects instead of files, for easier
testing.

0.3.1 (2012-02-16)
------------------

- Add bullet icons.


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
