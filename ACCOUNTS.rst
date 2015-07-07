Documentation on creation of user accounts
==========================================

All actions are done in the admin interface (
http://uploadservice.lizard.net/admin/ ) by user admin.

Creating an organization
------------------------

Every user is part of some (only one) organization. The organization
needs to exist first.


Creating a project owner organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to http://uploadservice.lizard.net/admin/lizard_progress/organization/add/

2. Enter the organization's name and description (for now, equal to its name)

3. Carefully choose the configured error messages for this
   organization. Not choosing them sensibly will lead to very
   confusing behaviour.

4. Check "is project owner".

5. Save.

6. On the next page, it is possible to change this organization's default values
   for all the config options.


Creating an uploading organization
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Go to http://uploadservice.lizard.net/admin/lizard_progress/organization/add/

2. Enter the organization's name and description (for now, equal to its name)

3. Select the first error message. This has no effect whatsoever, but
   it's currently impossible to save this page without selecting some message.

4. Save. (Do not check "is project owner").

The only difference between the two is that non-project owning organizations can
not make users that are project managers, and therefore can't make projects.


Creating a user
---------------

There are three roles for users: uploader, project manager, and admin
(user manager).

Users without roles are "just users". They can only *view* all the
project data their organization is involved in.

The first user of a new organization should be a user manager, so that
he or she can create more users as needed.

Uploading organizations should probably make all of their users
uploaders.

In project owning organizations, the project managers are the ones
that can create new projects, configure them, plan them, et cetera.

Adding a new user in the Django admin is a bit involved, because
unfortunately we don't automatically create user profiles.

1. Go to http://uploadservice.lizard.net/admin/auth/user/add/

2. Enter username and password, save. Use 'firstname.lastname' (lower
   case, no quotes) as username.

3. On the page you arrive at, it is probably a good idea to add the
   user's first and last names and an email address.

4. Now we make a UserProfile. Go to
   http://uploadservice.lizard.net/admin/lizard_progress/userprofile/add/

5. Select the user, his organization, and his roles. If this is the
   first user in the organization, include 'Gebruikersbeheerder'. Hold
   down the CTRL key to select multiple roles.

6. Save this page too.

New users for this organization can be added by this user from the normal
Uploadservice interface.


Administration
--------------

If a user has lost his or her password, it is not possible to look it
up in the database. However, it's possible to set a new one under Auth
-> Gebruikers.
