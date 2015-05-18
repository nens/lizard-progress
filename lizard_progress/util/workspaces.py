# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Helper functions for adding things to lizard-map workspaces."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from lizard_map import models


def get_workspace(request):
    return models.WorkspaceEdit.get_or_create(
        request.session.session_key, request.user)


def set_items(request, workspace_items):
    """Workspace items is a list of dictionaries, containing a name, an
    adapter name and the adapter_json of a workspace layer. Layers
    that don't exist yet are created, layers not in workspace_items
    are removed."""

    workspace = get_workspace(request)

    existing_items = {
        (item.name, item.adapter_class, item.adapter_layer_json): item
        for item in workspace.workspace_items.all()
    }

    for index, item in enumerate(workspace_items):
        key = (item['name'], item['adapter_class'], item['adapter_layer_json'])
        if key in existing_items:
            # Don't set visible -- this code is also called when visibility
            # is toggled.
            old_item = existing_items[key]
            old_item.index = index
            old_item.clickable = True
            old_item.save()
            del existing_items[key]
        else:
            models.WorkspaceEditItem.objects.create(
                workspace=workspace,
                name=item['name'],
                adapter_class=item['adapter_class'],
                adapter_layer_json=item['adapter_layer_json'],
                index=index,
                visible=True,
                clickable=True)

    # All the items still left in existing items need to be deleted
    for old_item in existing_items.values():
        old_item.delete()
