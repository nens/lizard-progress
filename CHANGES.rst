Changelog of lizard-progress
===================================================


1.31 (unreleased)
-----------------

- Export runs that don't generate files can now also show that they
  have run and whether they are up to date.

  It used to be the case that all export runs generated a file, and
  the check to see if they had run successfully some time in the past
  looked for the presence of this file. But the 'Export to Lizard'
  export run exports data to elsewhere, and doesn't have a file. There
  is now a new property, 'available', and for runs without generated
  files it merely checks for a created_at date. User interface now
  uses that, except for the Download link, which still needs a
  'present' file.

- Date of latest update is now based on the latest timestamp of
  Measurement, not ScheduledMeasurement. Because measurements can be
  updated and then the ScheduledMeasurement doesn't get a new
  timestamp.


1.30 (2013-06-26)
-----------------

- Fix missing location shapefiles.

- Initially upload files to a newly created tempdir in
  BUILDOUT_DIR/var/lizard_progress/uploaded_files, instead of in
  /tmp. /tmp is periodically cleaned up leading to loss of files.

1.29 (2013-05-31)
-----------------

- Improved Export to Lizard: now updates (not just inserts) database
  information, and saving to a directory (on some share) is supported
  as well.


1.28 (2013-05-31)
-----------------

- Add a name field to LizardConfiguration for ease of use.


1.27 (2013-05-07)
-----------------

- Add an "Export to Lizard". This uses a LizardConfiguration model
  that stores information about a Geoserver database and an FTP
  server, generates DXF, CSV and PNG representations of the profiles
  and puts them on the FTP server, then updates the geoserver database
  with the new information.


1.26 (2013-05-06)
-----------------

- Add handy impersonate middleware.

- Make process_uploaded_file wait until a file actually exists, it
  seems a problem with uploaded files crashing is caused by a race
  condition: the file is closed and then the task is started, but it's
  not immediately visible to other processes yet. Sleeps at most 10
  seconds, then marks the file as failed. Hopefully fixes #88.

- Call show_measurement_type() with the right kind of measurement type.
  Fixes #89.


1.25.1 (2013-04-25)
-------------------

- Some more tweaks to various templates, so that they still look
  reasonable if nothing has been uploaded yet.


1.25 (2013-04-24)
-----------------

- Projects are now ordered by name.

- Both map layers and exports are now only shown if there are actual
  scheduled measurements for this contractor/measurement type
  combination.

- Only show the 'all measurement types' map layer if there is more
  than 1 measurement type for this contractor/measurement type
  combination.


1.24 (2013-04-24)
-----------------

- Location shapefiles didn't show up because the view called them
  "location_shapefiles" and the template looked for "shapefiles"...


1.23 (2013-04-24)
-----------------

- Fixed bug #83 -- osgeo.ogr can't handle Unicode field names.


1.22 (2013-04-23)
-----------------

- Added a check to see if Z1/Z2 aren't too low _compared to the
  waterlevel_ instead of NAP (MET_Z_TOO_LOW_BELOW_WATER).

- Added a check to see if a measurement point is not too far away from
  the line between the 22 codes (MET_DISTANCE_TO_MIDLINE).


1.21 (2013-04-23)
-----------------

- It's now possible to save an Organization in the admin without
  filling in all the config options.

- Layout of the 'werkzaamheden toevoegen' wizard is slightly more clear,
  but really those pages should be refactored entirely.


1.20 (2013-04-22)
-----------------

- Instead of crashing, we now give error messages in case an expected
  shapefile field doesn't exist. Both when uploading measurement
  location shapefiles and hydrovakken shapefiles.

- There is also an error message in case of duplicate hydrovak IDs.


1.19 (2013-04-22)
-----------------

- Show which project and which page are currently selected.

- Fix bug where a wrong date format resulted in an infinite loop.


1.18 (2013-04-19)
-----------------

- Call hydrovakken layer "Hydrovakken <project name>" instead of just
  Hydrovakken.

- Add an extent to normal layers (gives them the zoom icon).

- Increased length of error_code database field -- this probably fixes
  the bug where a file would have errors, but then they couldn't be
  found in the database.

- Hydrovakken map lines are now thicker and blue (#67).

- Fix ExportRun up_to_date property (now uses Measurement's timestamp,
  instead of measurement date)


1.17 (2013-04-16)
-----------------

- Fix issue where configured ID in measurement shapefile didn't work.

- Users without add_project permission don't get to see the Beheer and
  Configuratie screens.

- Organization config can now be changed in the admin (onder Organization).

- After creating a project, user is redirected to the configuration page.


1.16.2 (2013-04-11)
-------------------

- Fix bug with finding config option for location_id.


1.16.1 (2013-04-08)
-------------------

- Small change, add a default error message if it is missing.


1.16 (2013-04-08)
-----------------

- Make the fields used in location and hydrovakken shapefiles
  configurable.


1.15 (2013-04-05)
-----------------

- Remove the option to upload a .prj file with shapefiles, because it
  didn't really work. Basically using RD_New shapefiles is mandatory
  now.

- If new Hydrovakken are uploaded, this project's old Hydrovakken are first
  discarded.

- Add per-organization and per-project configuration, and a screen to edit
  the per-project config options.

- Add new checks (MET_WATERWAY_TOO_WIDE, MET_Z_TOO_LOW,
  MET_INSIDE_EXTENT, MET_MEAN_MEASUREMENT_DISTANCE)

- Make checks depend on the config options (for instance, what the
  maximum allowed waterway width is)

- Foutmeldingen aangepast zodat zo zoveel mogelijk de ingestelde waarden laten
  zien in de foutmelding

- Remove the organization's allow_non_predefined_locations setting -
  we use configuration for that now.

- Make choosing errors for an organization in the admin interface easier.


1.14 (2013-04-03)
-----------------

- Fix bug with calling record_error_code() (#54).


1.13 (2013-04-03)
-----------------

- Fix MET file export (#45).

- Get all downloads to actually work (#41, #46).


1.12 (2013-04-02)
-----------------

- The downloadable files are under separate headers now, issue #41.


1.11 (2013-04-02)
-----------------

- Upload page overview tables now run on Javascript, an URL that
  returns the list of uploaded files as JSON, and an URL that can be
  POSTed to to delete them. Tables can be reloaded quite naturally,
  without refreshing the page.


1.10 (2013-03-29)
-----------------

- Make it possible to export MET files with sorted measurements.

- Improve CSV export: XY coordinates are now the midpoint of the
  water, water level is calculated from the 22 points, code could be
  made shorter a bit.

- Have we finally fixed the upload dialog button bug? It appears to
  have been some sort of Jquery UI version conflict

1.9.1 (2013-03-29)
------------------

- Fix bug with downloading files, mistyped a variable.


1.9 (2013-03-28)
----------------

- Improve DXF rendering: add the water line, a title and the z1 values
  at each measurement.

- Admin can't login anymore to the normal pages; you need to be part
  of some Organization, or there are too many pages that don't make
  any sense.

- Fixed showing Organization everywhere.

- Improvements to dwarsprofiel graphs:
  - Sort data points based on their projection on the baseline
  - Show distances to the midpoint on the X axis
  - Show the water level
  - Show project name, contractor name

- Add a log database model that logs each upload. For now, use it to show
  a 'latest uploads' table on the front page.

- Remove all content buttons except for 'zoom to default location'

- Make styling of the tables in the interface more consistent

- table-hover makes it look like rows can be clicked. In the cases
  that that makes sense (project list on the front page, uploaded
  files with errors) we make them clickable, in other tables remove
  table-hover.

- Update site title, no longer just HDSR Upload Server

- Remove collage edit from Kaartlagen page

- Uploaders and project organizations go to the same project page

- Some minor layout fixes

- Cleaned up a lot of code to do with directories, put it in
  util/directories.py

- Put hydrovakken, location shapefiles, organization files, result
  files and contractor reports all in the same table on the Downloads
  page

1.8.1 (2013-03-27)
------------------

- Fix for download page: it crashed if there were no measurements to
  download yet.


1.8 (2013-03-27)
----------------

- Automatically test example MET files.

- Fix bug with generating some types of exports.

- Fix some obvious bugs in met_parser brought to light by tests

- Show project owner's organization in the project list for uploaders


1.7 (2013-03-25)
----------------

- Dwarsprofielen is a measurement type that doesn't _need_ predefined
  locations. But it _can_ still use them, and give error messages if
  an uploaded profile doesn't correspond with a predefined location.

  Therefore, it's got "likes_predefined_locations" True. It is then up
  to the Organization whose project this is to decide what they want;
  for that purpose, an Organization has a
  "allows_non_predefined_locations" setting. This also controls
  whether locations can be predefined at the project management
  screen.

- Being uploader or project owner is now a property of Organizations,
  not of users.

- There is now an overview of the work of contractors on the Dashboard
  page

- Show which organization is logged in, besides the icon saying which
  user is logged in

1.6.1 (2013-03-22)
------------------

- Nothing changed yet.


1.6 (2013-03-22)
----------------

- Only Contractors get to see a project's Upload page.

- Add more Waternet checks, including checks on measurements in pairs
  (difference between consecutive Z1 values, ordering of X values,
  etc).

- Add checks that work on _sorted_ measurement rows, for Almere, where rows
  are not in the right order.

- Data is now saved sorted in the database, so graphs should come out right in
  most cases.


1.5 (2013-03-21)
----------------

- Implement checks for Waternet profile_point_type rules.

- Add export possibility. An export overview is on the Download page
  of a project. From there export runs can be started, that run as
  Celery tasks. One type of export is implemented: a zip file
  containing the most up to date uploaded files. Files can be
  downloaded.

- Added exports as MET file.

- Added CSV, DXF exports.


1.4 (2013-03-19)
----------------

- Fix dwarsprofiel graph, was broken in latest Lizard


1.3 (2013-03-15)
----------------

- Move document_root and make_uploaded_file_path functions to
  process_uploaded_file.py, to prevent circular imports.
- Made a Celery task that calls process_uploaded_file, and call this
  task from the upload view after uploading a file.
- Add UserProfile, Organization models.
- Replace user with organization in Contractor model.
- Fix has_access method.
- Fix wizard's froms ProjectorForm and ContractorForm.
- Create method to list users of same organization
- Removed unused forms.
- Added an error page. If there are errors with line numbers, it shows
  the entire file with the erratic lines in red. Errors without line
  numbers are shown in a simple list.
- Added error messages for MET files.
- Added functions to Project and Contractor that make sure their slug
  is always globally unique (no problems with the same project name
  in different organizations)
- Made sure that the combination project/organization as a contractor
  is always unique
- Create 'progressbase' template.
- Rebuild template 'dashbord', 'upload', 'download' to extend progressbase template.
- Fix logou.
- Order navigation in site.
- Add field 'profiletype' to UserProfile model to make difference between
  contractor and projectmanager.
- Extend views with ProjectsView, UiView, View.
- Helper methods "get_by_user" for Organization, UserProfile.
- Fix breadcrumbs (now using standard Lizard functions)
- Fix links to project pages (now using {% url %} template tags)
- Improve layout of project pages
- Add remove link to uploaded files
- Hopefully fix bug with plupload (issue lizard_progress #16) (add an
  extra refresh() call after it becomes visible)
- Create locations if they don't exist yet and organizations wants that
- Create scheduled measurements if they don't exist yet and organization wants
  that
- Move CSV download to downloads instead of dashboard
- Move project admin into the sidebar
- Sort out view subclassing
- Add contractor to progress graph
- Update lizard versions for testing


1.2 (2013-03-05)
----------------

- Lots of work to make it possible to have several error messages for
  a file parse, use of metfilelib.parser.

- Instead of immediately parsing an uploaded file in the view, it is
  now saved as an UploadedFile, and can be processed in the
  background. There is a new upload page that shows the status of
  uploaded files.

- Some simplifying work, but the way measurement types are tied to
  projects is still far too complicated.

1.1 (2013-02-27)
----------------

- Fixes to make the app work in uploadserver-site (standing alone).


1.0.4 (2012-09-28)
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
