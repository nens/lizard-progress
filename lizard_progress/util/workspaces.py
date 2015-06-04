# (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.rst.
# -*- coding: utf-8 -*-

"""Helper functions for adding things to lizard-map workspaces."""

# Python 3 is coming
from __future__ import unicode_literals
from __future__ import print_function
from __future__ import absolute_import
from __future__ import division

from collections import namedtuple

from lizard_map import models

# We tried to save workspace items for which the name was too
# long... restrict them.
MAX_NAME_LENGTH = (
    models.WorkspaceEditItem._meta.get_field_by_name('name')[0].max_length)


class MapLayer(namedtuple(
        'MapLayer', 'name adapter_class adapter_layer_json extent')):
    """Class that represents a map layers that can be added to a lizard-map
    WorkspaceEdit."""
    def __init__(self, name, adapter_class, adapter_layer_json, extent=None):
        """Allow omitting the extent."""
        return super(MapLayer, self).__init__(
            name, adapter_class, adapter_layer_json, extent)

    @property
    def truncated_name(self):
        return self.name[:MAX_NAME_LENGTH]

    @property
    def key(self):
        return (self.truncated_name,
                self.adapter_class,
                self.adapter_layer_json)


def get_workspace(request):
    return models.WorkspaceEdit.get_or_create(
        request.session.session_key, request.user)


def set_items(request, map_layers):
    """Layers that don't exist yet are created, layers not in
    workspace_items are removed.

    """

    workspace = get_workspace(request)

    existing_items = {
        (item.name, item.adapter_class, item.adapter_layer_json): item
        for item in workspace.workspace_items.all()
    }

    for index, map_layer in enumerate(map_layers):
        key = map_layer.key
        if key in existing_items:
            # Don't set visibility here -- this code is also called
            # when visibility is toggled.
            old_item = existing_items[key]
            old_item.index = index
            old_item.clickable = True
            old_item.save()
            del existing_items[key]
        else:
            models.WorkspaceEditItem.objects.create(
                workspace=workspace,
                name=map_layer.truncated_name,
                adapter_class=map_layer.adapter_class,
                adapter_layer_json=map_layer.adapter_layer_json,
                index=index,
                visible=True,
                clickable=True)

    # All the items still left in existing items need to be deleted
    for old_item in existing_items.values():
        old_item.delete()
