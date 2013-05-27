Documentation on creation of user accounts
==========================================

All actions are done in the admin interface (
http://uploadserver.lizard.net/admin/ ) by user admin.

Creating an organization
------------------------

Every user is part of some organization. This needs to exist
first. There are two kinds of organization: Project owning
organizations, and uploading organizations. An organization cannot be
both.

Creating a project owner organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to http://uploadserver.lizard.net/admin/lizard_progress/organization/add/

2. Enter the organization's name and description (for now, equal to its name)

3. Carefully choose the configured error messages for this
   organization. Not choosing them sensibly will lead to very
   confusing behaviour.

4. Check "is project owner".

5. Save.

Creating an uploading organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to http://uploadserver.lizard.net/admin/lizard_progress/organization/add/

2. Enter the organization's name and description (for now, equal to its name)

3. Select the first error message. This has no effect whatsoever, but
   it's currently impossible to save this page without selecting some message.

4. Save.

Creating a user
---------------

There are two kinds of users: normal users and project managers.

Uploading organizations only have normal users, and all of them are
exactly the same.

In project owning organizations, the project managers are the ones
that can create new projects. However, any normal user can become the
superuser of some project (this is done while creating the
project). So creation of projects and being superuser of one project
are different concepts.

Only step 4 is different for project managers:

1. Go to http://uploadserver.lizard.net/admin/auth/user/add/

2. Enter username and password, save

3. On the page you arrive at, it is probably a good idea to add the
   user's first and last names and an email address.

4. FOR A PROJECT MANAGER, also select the group "Projectmanagers" at
   the relevant spot.

5. Save this page too.

6. Now we need to connect the new user to the organization. We do that
   by adding a User Profile, at
   http://uploadserver.lizard.net/admin/lizard_progress/userprofile/add/
   .  Select the newly created user and the right organization, and
   save.


Administration
--------------

If a user has lost his or her password, it is not possibly to look it
up in the database. However, it's possible to set a new one under Auth
-> Gebruikers.
