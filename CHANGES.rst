Changelog of lizard-progress
===================================================


1.0.4 (unreleased)
------------------

- Improvements to GUI.


1.0.3 (2012-09-21)
------------------

Fix the call to Realtech code, moving the resulting zipped shapefile
afterwards.


1.0.2 (2012-09-13)
------------------

Moved result of calling Realtech's code to the correct directory.


1.0.1 (2012-09-12)
------------------

Fixed shaky dependencies on where exactly files were uploaded when
using them for checks. Now we look in all subdirectories too to find
the newest file.


1.0 (2012-09-12)
----------------

- Nothing changed yet.


0.14 (2012-09-05)
-----------------

Reworked the model a bit:
- Added an AvailableMeasurementType model
- Changed the MeasurementType model so that it functions as if it were
  the "through" table in a many-to-many relationship between Project
  and AvailableMeasurementType.

- Location's primary key is now a normal AutoField (took six
migrations to do that, see
http://stackoverflow.com/questions/2055784/what-is-the-best-approach-to-change-primary-keys-in-an-existing-django-app/12247601#12247601
)
- Location's "unique_id" is renamed to "location_code", because it's
  not necessarily unique anymore.

The way that lizard-progress talks to implementing sites has
changed. Instead of a "Specifics" implementation per project, there is
now one per measurement type. See the HDSR site for details (in its
setup.py and progress.py).

Added a field "can_be_displayed" to AvailableMeasurementType. Types
that can't be displayed on the map will have this False, the default
is True. Measurement types that can't be displayed do not show up at
the available map layers and don't have popups either. Only locations
with the_geom not equal to NULL are used for maps.

0.13 (2012-07-13)
-----------------

Two changes:

- Non-image files are now opened in 'rU' mode, universal line ending
  mode. This should fix a problem some people at Van der Zwaan had
  with uploading MET-files with Mac-line endings.

- Sending a file with no measurements in it now results in an error
  message, not an internal server error.


0.12.1 (2012-06-05)
-------------------

- Added missing templates...


0.12 (2012-06-05)
-----------------

Added a screen to compare measurements taken by different contractors.

- "Comparison" screen shows a list of measurement types, and for each
  type, a list of locations where more than one contractor has taken
  a measurement
- Popup that can show measurements by different contractors side by side


0.11.1 (2012-05-23)
-------------------

- Nothing changed yet.


0.11 (2012-05-04)
-----------------

- Added create_zipfile command


0.10 (2012-04-11)
-----------------

- Successful measurements can still have an empty list of measurements,
  because parsers can now be called with "check_only=True", which doesn't
  save anything to the database and only runs checks.

- Added script that runs parsers in check_only mode on all files
  uploaded so far.

- Added factory_boy for easy testing.

0.9 (2012-03-21)
----------------

- Fix error message so that it only shows the basename of uploaded
  file.

- Downloadable CSV files for each contractor in a project, so that
  they have an overview of which things are still missing and which
  files were uploaded.

0.8 (2012-03-08)
----------------

- Show popups (and hover info) regardless of whether the measurement
  is complete or not.

- Added a new popup, used in case of noncomplete data, that just says
  what the location ID is and that it is incomplete.

- Fixed an odd bug with uploading multiple files, errors and
  chunking. By turning off chunking.


0.7.2 (2012-03-02)
------------------

- Fixed line number in error messages.


0.7.1 (2012-03-01)
------------------

- Fixed error in specifics.ProgressParser.error()


0.7 (2012-03-01)
----------------

- Bug fixing (previous version didn't work at all).


0.6 (2012-03-01)
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
