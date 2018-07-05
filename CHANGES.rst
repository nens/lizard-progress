Changelog of lizard-progress
===================================================

4.1.11 (2018-07-05)
-------------------

- Hotfix progresspar project dahboard.

- Only perform a max distance check when the Location is not newly created.

- Use midpoint for creating metparser Locations.

- Use midpoint for TOO_FAR_FROM_LOCATION change request.


4.1.10 (2018-06-20)
-------------------

- Hotfix Upload button.


4.1.9 (2018-06-18)
------------------

- Added some performance improvements for the startpage (projects). More caching, less repetitive calculations.


4.1.8 (2018-06-07)
------------------

- Fix circular import in upload_planning command.


4.1.7 (2018-06-07)
------------------


- Added progress field in ReviewProject + migration file.

- Removed progress test

- Add ``upload_planning`` management command (a temporary solution to files
  too large to be uploaded via the site).

- Some refactoring in PlanningView to make some methods static and callable
  from elsewhere.


4.1.6 (2018-06-06)
------------------

- feature_collection_geojson used in calc_progress().

- Set LENGTH_MULTIPLIER in RIBX angle measurement check
  to 4 for Almere.


4.1.5 (2018-05-28)
------------------

- Make creating a review project async as well.


4.1.4 (2018-05-28)
------------------

- Generate GEOJson for review projects in a task, save it on the model.

- Ignore all inclination angle measurements on import, for speed (saves
  90% of the JSON size).


4.1.3 (2018-04-18)
------------------

- Fixed GWSW logparsing.


4.1.2 (2018-03-05)
------------------

- Improved speed of review page: don't show the individual measurement points
  anymore in the inline geojson.


4.1.1 (2018-03-02)
------------------

- Disable 'download shapefiles' button in *beoordelingstool* if no shapefiles
  have been uploaded yet.


4.1 (2018-02-28)
----------------

- Beoordelingstool fixes.


4.0.0 (2018-02-12)
------------------

- Include the "Beoordelingstool."


3.20.1 (2017-12-06)
-------------------

- Bugfix for missing import in process_uploaded_file.

- Workaround for ``KeyError: u'logcontent'`` error when talking to the GWSW
  API, probably the logcontent key is missing instead of being empty when the
  check is not ready yet.


3.20 (2017-11-30)
-----------------

- Added last download and upload date for uploaded files.


3.19 (2017-11-01)
-----------------

- Disabled angle checks for simple projects.


3.18 (2017-10-18)
-----------------

- Using Dutch error messages.


3.17 (2017-10-13)
-----------------

- "Fixed" locations' completeness by adding a management command that fixes
  all locations that have been added in the last 15 minutes. We can adjust the
  time duration later on.


3.16 (2017-10-13)
-----------------

- Fixed a problem with locations' completeness which would not be updated
  correctly.


3.15 (2017-10-03)
-----------------

- Modernised setup a bit by adding docker and a Jenkinsfile.

- Fixed a non-working ``__init__`` in a weird subclassed namedtuple.

- Requiring at ribxlib > 0.10: this version parses more "observations"
  information which is needed for checking angle measurements.

- Added check for minimum number of angle measurements ("hellinghoek").


3.14 (2017-05-30)
-----------------

- Fix bug in ribx merge export due to unexpected comments in ribx file.


3.13 (2017-05-08)
-----------------

- Fix bug in GWSW check property.


3.12 (2017-05-03)
-----------------

- Fix crash in MET parser when no midpoint can be determined (to catch this
  error the 22 code check should be used). If there is no midpoint we will
  revert back to using the start point.

- Add simple project option


3.11 (2017-03-24)
-----------------

- Use profile midpoint instead of start_point for the ``TOO_FAR_FROM_LOCATION``
  check for metfiles.


3.10 (2017-02-16)
-----------------

- Improve Ribx merge strategy by identifying duplicates by their unique
  identifying fields and only saving them once.


3.9 (2016-12-13)
----------------

- Add two manuals.


3.8 (2016-12-07)
----------------

- Remove count() from Measurement.__unicode__() because it would generate
  a huge amount of ``COUNT(*)`` queries.

- Improve admin.

- Add completeness script.


3.7 (2016-10-21)
----------------

- Nothing changed yet.


3.6 (2016-10-13)
----------------

- Bump ribxlib to 0.6.

- Allow Ribx Pipe inspection to have multiple measurements.

- Add export option for merging Ribx files into one file.

- Code style fixes.


3.5 (2016-09-08)
----------------

- UI fixes in the DownloadHomeView template.


3.4 (2016-09-08)
----------------

- Added new kind of export. Like ``export_all_files()``, it exports all files,
  but to a directory instead of into a zipfile. This way, it can be synced via
  FTP. Files that don't need updating are left alone to save iops.

  To enable it, both the organization and the measurement type should have the
  "allow ftp sync" enabled.

- Fixed textual search in the admin for export runs.

- Disabled one-time migration 0031.


3.3 (2016-07-20)
----------------

- Fixed tests + updated directories.absolute function behavior.

- Make ProjectActivityMixin.latest_log also work with Activity.


3.2 (2016-07-14)
----------------

- Fixed JS bug where you couldn't delete users.


3.1 (2016-05-06)
----------------

- Archiving a Project is now a Celery task.


3.0 (2016-04-13)
----------------

- Merged whole redesign branch.


2.10 (2016-04-11)
-----------------

- Fixed nginx download.


2.9 (2016-04-08)
----------------

- Remco isn't (hardcoded!) mailed anymore upon task exceptions.

- Nginx is used to serve large files.

- Relative paths are used instead of absolute ones.


2.8.1 (2016-03-17)
------------------

- Bugfix of raw-sql migration.


2.8 (2016-03-17)
----------------

- Fixed sql script that creates a 'publiekskaart' view.
- Changed sql script into migration.


2.7 (2016-02-26)
----------------

- Implement a better solution for visualizing old and new locations of
  Move Changerequests.

- Changed Location.work_impossible and Location.new into NullBooleanField.

- Update publiekskaart SQL script.

- Re-add turquouise_dark ball for old Move Requests in map legend.

- Fix a bug when clicking on Requests.

- Visualize old location of Move Requests by using the another Request object
  (kinda ugly because that generates a new Request in the GUI).

- Add a new check for the uploaded shapefile schedule: if the week number is
  in the current or next week the day is mandatory. An error will be raised
  if that's not the case.

- Update legend and update translations.

- Fix a problem with the create_new method: geoms with a Z-value are not
  accepted, thus points are now converted to 2D.

- Disable the automatic Request generation for 'work_impossible' drains, now
  they are automatically completed and given a new color. Furthermore, newly
  created/unplanned drains are also given a new color.

- Add archiving tests.

- Bump lizard_map to 4.51.1 which contains a fix for JSONFields.

- Implement deletion of 'attachment' Measurements when Project is archived.
  This should only be done for sewerage projects; to enable deletion of a
  specific measurement type the delete_on_archive field must thus be set. The
  measurement types fixture is updated to reflect this change.

- Add delete_on_archive field to AvailableMeasurentType.


2.6.16 (2016-01-21)
-------------------

- Make an initial working version of the GWSW checker.

- Add missing models to admin.

- Typo...

- Remove the item for "old location of accepted change request" from
  the legend -- as this isn't stored in the database, and the location
  has moved successfully, we can't actually show this information on
  the map.


2.6.15 (2016-01-14)
-------------------

- Show only old locations from change requests in the actual project we're
  looking at.

- Fix clicking old location.


2.6.14 (2016-01-08)
-------------------

- When a "move location" change request is shown as a map layer, make the
  old location clickable as well. This results in the same popup (there is
  one popup per change request).


2.6.13 (2015-11-17)
-------------------

- Added graphical lines to the legend (instead of text like "a red line").

- Add change requests to the legend.


2.6.12 (2015-11-10)
-------------------

- Make export run path name longer (some exports went over the 300 limit).


2.6.11 (2015-11-10)
-------------------

- Add a field 'measured_date' to Location that is the latest of the 'date'
  fields of its measurements. Measurements that have no 'date' are ignored.
  This is used in the publiekskaart.

- Fix call to multidwarsprofiel graph.


2.6.10 (2015-11-02)
-------------------

- Fix bug with creating deletion requests for linestrings.


2.6.9 (2015-11-02)
------------------

- Slightly improve the code that sets locations to complete in
  ribx_parser (fewer queries, less dependence on transaction magic).


2.6.8 (2015-10-23)
------------------

- Call crosssection_graph.graph correctly in mtype_specifics.


2.6.7 (2015-10-22)
------------------

- Remove extra ``location__`` from filter.


2.6.6 (2015-10-21)
------------------

- Nothing changed yet.


2.6.5 (2015-10-21)
------------------

- Make old change requests work on the map, and add all of them to the
  list of layers.


2.6.4 (2015-10-19)
------------------

- Do not send any mails if a change request was made by the manager and
  auto-accepted.

- The "multiple projects dwarsprofiel graph" now filters locations based
  on their distance to one chosen location, not on location code.

- Activity names are now part of export filenames.


2.6.3 (2015-10-16)
------------------

- Fix bug where multiple ExpectedAttachments were returned by a filter()
  over a M2M relation.


2.6.2 (2015-10-12)
------------------

- Reloading the exported file page was very slow, and automatically
  repeated every second. Fixed that.


2.6.1 (2015-10-06)
------------------

- Add a extra field to Location to signal that this Location has at
  least one measurement, to make the Publiekskaart SQL a lot simpler.


2.6.0 (2015-09-09)
------------------

- The project dashboard page still looked at UploadedFiles to determine
  when the last upload was, but these can be deleted by users after uploading.

  It is better to use UploadLog instead, but those in turn still referred
  to a project/mtype/contractor combination instead of an Activity.

- Add check to see if two <METING> lines inside the same <PROFILE> do
  not have the same X and Y coordinates. This is the
  'MET_XY_OCCURS_ONCE_IN_PROFILE' error code.

- Exports are now saved to the <Organization>/ftp_readonly/ directory, where
  they can be served over FTP.

- Reworked expected attachments. The data model was changed: expected
  attachments now have a many two many field to the ``_measurements_``
  that said that those attachments were going to be sent, and they
  don't have a foreign key to Activity anymore (normalization).

- Made a method on Measurement that sets up the expected measurements
  for that measurement. This fixes a bug (uploading a new version of
  the same measurement with a corrected filename made the
  Uploadservice wait for both the old and the new file).

- A curious situation can occur if some RIBX file says it is going to
  upload some filename, then the file is uploaded, and later another
  RIBX file says it is going to upload the same filename. Is the same
  file meant or another? Supporting it being the same file leads to
  really complex code (as if it's not complex enough already) so we
  give an error message in this case.

- Add support for e-mail notifications.

- Add 'show change request on map' functionality.

- Filenames of uploaded files need to be unique, as different versions
  of the same file can be uploaded. We used to store them with a
  YYYYMMDD-HHMMSS-0- prefix, but that led to problems in the export,
  popup etc. Now we store each file in its own temporary directory
  with a similar prefix.

- Include a new management command (rename_measurements) that goes
  through all uploaded files and if they are in the old format, moves
  them to the new way. Incidentally also fixes an old bug where files
  were stored in the wrong directory.

- Remove a number of ancient management commands that aren't used anymore,
  and tools.py which was only used by those commands.

- Allow cancelling (deleting) a Measurement, from the popup. This will
  actually delete uploaded files (if there were no other measurements
  relating to it), which is a first. Only RIBX, for now. Handles
  attachments correctly. Send a notification.

- Change name 'Uploadserver' to 'Uploadservice' (note that this is purely
  a cosmetic change for the front-end).

- Change name 'Hydrovak' to 'Monstervak' (note that this is purely a
  cosmetic change for the front-end).

- Make it also possible to zoom to a specific Location, make that the
  location's get_absolute_url()

- Create a Remove change request when the RIBX file claims it was
  impossible to do part of the work.

- Allow RIBX files to note that some pipe, manhole or drain was new
  (not part of the assigned work), automatically add it to the
  activity and send an email.

- For some project types ("Calamiteiten"), show numbers on the map with
  the amount of non-attachment measurements for that location, if the
  number is more than 1 in the last 14 days.

- Added a legend.

- If a Dwarsprofielen location code is present in more than one
  project / activity of the same organization (all complete), there is
  now a link in the popup to a graph that shows all of them. This is
  to make it possible to compare multiple measurements over a number
  of years (it is not possible to view multiple projects at the same
  time on the map page anymore).

- Emails for new change requests now correctly say whether the request
  was made by a manager or an uploader.

- Presentation tweaks to prepare for the demo (popup, zoom levels).

- Add a warning for RIBX location planning if there already are
  locations.


2.5.2 (2015-06-12)
------------------

- A variable that should have been removed had one instance left, which
  caused the map page to crash.

- Added four ``__unicode__`` methods in models to help with debugging on
  the command line.

- Use allowZip64=True in export zipfiles, so that they can become
  larger than 2GB.

- The popup should already show if a location has at least a single
  measurement, not just when it is complete.


2.5.1 (2015-06-11)
------------------

- Missed () after a function name, which caused a bug with checking if
  a measurement is complete after uploading an expected attachment.


2.5.0 (2015-06-10)
------------------

New features for the Almere / HDSR project:

- Cleaned the map page; all layers of the current project are
  automatically in the workspace, and the extent is set to the current
  project's. Items can't be removed, only their visibility can be
  toggled. No secondary sidebar, no collage.

- Options can now belong to measurement types, and are only shown if
  the current activity actually uses that type.

- There are measurement types that use the implementation of other
  measurement types. They seem different to the user, but are the same
  internally. It is now possible to configure separate organization defaults
  for these, so that e.g. the dwarsprofiel measurement at the start of a
  project can use different distance defaults than the measurement made at
  the end of a project.

- Add expected attachments to popup, if present

- Fix bug where uploaded files were saved to the wrong directory.

- Improve date formatting

- Extent config options (min X, min Y, etc) are now not just for MET files
  anymore, they are also used when checking RIBX files.

- For convenience's sake, they are configured at project level instead
  of activity level.

- Ownership of locations stuff:

  When Almere uploads a RIBX file to plan a project, they include
  information on drains not owned by Almere. Contractors do not need
  to clean / inspect these, but by putting them in the planning info,
  it is known that they are not actually new when contractors find
  them.

  * RIBX drains have a <EAQ> field that signifies ownership. Our
    ribxlib puts this information in the "owner" attribute of
    drains. Almere uses "A" for owned by Almere, "B" for privately
    owned, and "C" for unknown. The Uploadservice only cares about
    "owned by project owner" and "other".

  * There are two config options, one where it can be configured that
    the code to look for is "A", the other to signify that a project
    cares about ownership like this.

  * Planning these locations sets the "not_part_of_project" flag of
    locations.

  * They are shown as grey balls on the map, regardless of what was
    uploaded for them. There is also a message in the popup.

  * They are not counted wherever there are statistics about numbers
    of locations.

  * Their can't be a date planned for them.

  * They are not included in the shapefile export.


- All "percentage done" items were shown as "N/A" due to an
  accidentally deleted "not", fixed.

- Map layers for change requests are now shown on top of normal map
  layers, not under them.


2.4.7 (2015-05-08)
------------------

- Bug fixes:

  - A project's slug field must be allowed to be longer than its name
    field, now set to 60 instead of 50.

  - Configuration.get was called with project as an argument, must be
    an activity now.

  - Hydrovak adapter (to show them on the map) had a typo, so they
    didn't show.

  - Showing open and closed change requests now correctly only shows the
    requests for the current activity.

  - For showing who did the last action for a change request, we consider
    a newly opened change request to be last acted on by the contractor.

  - The upload log on the front page now correctly shows the time of the
    latest upload, not the first...

  - The "Export to Lizard" export used outdated model relations.

  - The "MET_WRONG_PROFILE_POINT_TYPE" check checked the logical opposite
    of what it should check...

  - The "Export CSV" button was never implemented, but was still visible.
    This led to complaints. Removed it.



2.4.6 (2015-04-15)
------------------

- Set plupload upload limit to 10GB instead of 1GB.


2.4.5 (2015-03-03)
------------------

- Reinstate the option to give names to Activities when adding them.


2.4.4 (2015-03-02)
------------------

- Fix bug calculating the Nginx path for export downloads.


2.4.3 (2015-02-24)
------------------

- Fix bug where planning a project using a point shapefile didn't work
  anymore.


2.4.2 (2015-02-09)
------------------

- Improved the speed of the date planning view, using objects.update()
  on only the exact list of location ids that need to be updated to a
  date.


2.4.1 (2015-02-06)
------------------

- Check if the shapefile uploaded to plan locations of an activity is
  a Point shapefile. Previously, if another geometry type was
  uploaded, this resulted in Internal Server Error, now it gives an
  error message.

- Optimize planning locations using RIBX; this makes it impossible to
  move existing locations that have measurements, but makes it possible
  to plan using a single (~19MB) RIBXA file that contains the entirety
  of Almere's sewer system.


2.4.0 (2015-01-30)
------------------

- Declared migration bankruptcy. If you are upgrading an existing
  database, first checkout lizard-progress 2.3.2 and run its
  migrations.  Then run::

    DELETE FROM south_migrationhistory WHERE app_name = 'lizard_progress'"

  upgrade lizard-progress to your desired version and fake the
  initial (0001) migration.

  The same action is required for the changerequests subapp.

- Storing Geometries instead of Points now for Locations and Measurements,
  so that they can be lines as well. Adapted the adapter.

- Support RIBX and RIBXA formats for sewerage data, using ribxlib.

- Support *date planning*; shapefiles can be uploaded that describe when
  certain locations will be inspected. Map colors use this.

- Add a little wrinkle to MET files checks for HHNK: they check if a
  MET profile starts with 1 and ends with 2, except it's also allowed
  to have 99 codes outside those.


2.3.2 (2015-01-15)
------------------

- Fix "Export to Lizard", which was still using the old DB structure.


2.3.1 (2015-01-07)
------------------

- Added a script that migrates files to the new activity-based
  directory structure.


2.3 (2014-12-03)
----------------

- Projects now have one or more Activities, which have a single
  MeasurementType and a single Organisation working as contractor.
  This led to changes *everywhere*.

- Speedups (mostly cache result of has_access).

- Ubuntu 14 compatibility (new mapnik!)

- Show 5 activity fields in the New Project form, not 3.

- Do not let users pick an activity name in the New Project form.

- Fix showing the date of an Activity's latest upload.

- When showing an Activity's last uploader, use username if the user
  has no first and no last name.

- Add a check that gives an error if MET file profile point types
  5, 6 or 7 have a Z1 or Z2 level that is above the waterlevel
  (MET_Z_ABOVE_WATERLEVEL).

- Remove the special topbar for activities, this saves user clicks
  and although it is ugly, it's not uglier than what we had.

- Reorganize directory structure of files, there are activity
  directories now.

- Fix progress CSV file generation.



2.2 (2014-07-04)
----------------

- Show number of open change requests on the projects page.

- Add a tooltip to the upload buttons.

- AvailableMeasurementTypes now have an "implementation". Several
  types may share the same implementation, and thus do the exact same
  thing. If no implementation is given, the "slug" field is used, so
  that for types for which this feature isn't used, nothing changes.

- We can now configure which AvailableMeasurementTypes are allowed for
  each organization. In the same models, the organizations will be
  able to say which of those they want to be visible.

- By default, everything that already existed is allowed and visible.

- New project page only shows visible measurement types.

- Both planning pages only show visible measurement types.

- There is a "Edit visibility" page where visibility of measurement
  types can be edited. Accessible from the new project page.

- In order to be able to distinguish between various measurement types
  that use the same files, we know use a separate upload button for
  each type, and store the mtype in the UploadedFile model.

- Parsers now use that stored mtype.

- Fix lab csv parser so that it can handle multiple measurements in
  one file.


2.1.5 (2014-04-14)
------------------

- Increase the length of some database fields, e.g. too short Hydrovak
  IDs led to errors.


2.1.4 (2014-04-08)
------------------

- Add a 'refresh_hydrovakken' management command that reloads existing
  Hydrovakken shapes into the database.


2.1.3 (2014-03-18)
------------------

- Images can be shown again (Django served them from the wrong
  directory).

- Images can be uploaded again (Once upon a time we created, but
  never used, the FILE_IMAGE file type).

- Peilschaal CSV files now don't need predefined scheduled
  measurements anymore, although it's very good to have them, because
  the CSV files lack geom info. Turning the check back on in the admin
  after a manual import.


2.1.2 (2014-03-06)
------------------

- If an export fails, send an email.

- A DXF export will fail if it wasn't possible to retrieve the
  necessary profile.


2.1.1 (2014-03-04)
------------------

- Export runs that crash will now be recorded as stopped, and show an
  error message.


2.1 (2014-02-18)
----------------

- Change requests page: contractors can ask to remove, move or create
  new locations.

- View and judge change requests using the map.

- Archive projects.

- Possible requests: some errors (unknown locations, moved locations)
  can potentially be fixed with requests. This is recorded and the
  uploader can quickly requests the necessary changes. If all errors
  of the file are like this, and the requests are all accepted, then
  the file is re-uploaded.

- Check distance to planned location for MET files.

- Added a page where contractors and measurementtypes can be added to
  and removed from projects.

- Location shapefile can now be downloaded as an export (that can be
  updated). Downloading the original shapefile is now disabled, as it
  can be out of date.

- Don't allow new requests for location codes that already have an
  open request, not even if one of them is only the old_location_code

- Auto-accept requests made by a project manager

- Fix bug with zooming onto a single point with Mapnik (it's not a
  *nice* fix, but it works)

- Add extent to changerequest map layers

- After uploading an organization or project file, put all shapefile parts
  into a ZIP file.

- Add Handleiding.

- Add detail about coordinates to change request detail page and popup.

- Fix progress graphs.

- Put the right measurements into the location shapefile.


2.0.3 (2013-11-28)
------------------

- Fix next bug, can't lookup unicode field names with ogr.


2.0.2 (2013-11-27)
------------------

- Check if ID field name exists when importing shapefiles, better
  inform user.


2.0.1 (2013-11-26)
------------------

- Fix bug to open a shapefile in case of unicode filename.


2.0 (2013-11-11)
----------------

- Add user roles. A userprofile can now have one or more roles.

- Organization is now a property of a project. Before, the
  organization of the project's superuser was used.

- There is a new 'new project' page.

- Scheduling measurements now goes through the 'Planning' page, available
  on the Dashboard.

- Show the organization's downloads and the shapefile downloads in
  separate tables

- Upload and delete organization files.

- Added a page where organizations can edit the default values for
  configuration values of checks.

- Add user management pages. An organization can now manage its own
  users.

- Fix bugs where map layers didn't have icons, contractors didn't have
  names.

- Only show lines with errors in them, unless a checkbox is ticked.

- Only organizations with projects can assign the project manager role.


1.38 (2013-10-18)
-----------------

- Further fix IE bug (it caches Ajax requests).


1.37 (2013-10-10)
-----------------

- Nothing changed yet.


1.36 (2013-10-10)
-----------------

- Plupload won't work in Internet Explorer. This version implements a
  very basic form for such browsers that just uploads one single
  file. This will be particularly annoying for shapefiles, but at
  least IE can be used now.


1.35 (2013-08-23)
-----------------

- Fix Hydrovakken upload so that it works with mixed LineString /
  MultiLineString content.

- Try to fix plupload for Internet Explorer.


1.34 (2013-08-20)
-----------------

- Fix wrong percentage (b/a instead of a/b)

- Fix bugs with removing uploaded files


1.33 (2013-08-13)
-----------------

- Increase max size of uploaded files (4mb to 1000mb -- don't know if
  it keeps working, but the old limit was also arbitrary).


1.32 (2013-08-13)
-----------------

- Uploaded report files can now also have .zip and .doc extensions, instead
  of only .pdf.

- Sort downloadable files.


1.31 (2013-07-12)
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

- Added a check to see if Z1/Z2 aren't too low *compared to the
  waterlevel* instead of NAP (MET_Z_TOO_LOW_BELOW_WATER).

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

- Dwarsprofielen is a measurement type that doesn't *need* predefined
  locations. But it *can* still use them, and give error messages if
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

- Add checks that work on *sorted* measurement rows, for Almere, where rows
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

- Location's primary key is now a normal AutoField (took six migrations to do
  that, see
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

- Parsers now receive file objects instead of files, for easier testing.

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
