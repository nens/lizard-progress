// (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

// jslint configuration
/*global $, map */

// Upload popup
$().ready(function () {
    var $dialog;

    $url = $("#iconbox").attr("data-upload-url");

    $dialog = $('<div class="lizard-progress-popup"/>').load($url).dialog({
        autoOpen: false,
        title: 'Uploaden',
        width: 500
    });

    $('.upload').click(function () {
        $dialog.dialog('open');
        // prevent the default action, e.g., following a link
        return false;
    });

});

// Dashboard popup
$().ready(function () {
    // Clicking on an area in the dashboard view
    var $dialog = {};

    $('.dashboard').click(function () {
        var area_slug = $(this).attr('data-area-slug');
        var area_name = $(this).attr('data-area-name');
        var contractor_slug = $(this).attr('data-contractor-slug');
        var contractor_name = $(this).attr('data-contractor-name');
	var dashboard_url = $(this).attr('data-dashboard-url');

        if ($dialog[contractor_slug+area_slug]) {
            $dialog[contractor_slug+area_slug].dialog('open');
        } else {
            $dialog[contractor_slug+area_slug] = $('<div class="lizard-progress-popup"/>').dialog({
                autoOpen: true,
                open: function (event, ui) {
                    $(this).load(dashboard_url);
                },
                title: 'Voortgang '+contractor_name+' Deelgebied ' + area_name,
                width: 630,
                height: 420
            });
        }
    });
});

$().ready(function () {
    // Clicking on a location to be compared
    var dialogs = {};

    $('.comparison').click(function () {
	var comparison_url = $(this).attr('data-comparison-url');
	var location_unique_id = $(this).attr('data-location-unique-id');
	var measurement_type = $(this).attr('data-measurement-type');

	var dialog_key = comparison_url + location_unique_id;

	if (dialogs[dialog_key]) {
	    dialogs[dialog_key].dialog('open');
	} else {
	    dialogs[dialog_key] = $('<div class="lizard-progress-popup"/>').dialog({
		autoOpen: true,
		open: function(event, ui) {
		    $(this).load(comparison_url);
		},
		title: 'Vergelijking '+measurement_type+' Locatie '+location_unique_id,
		width: 900,
		height: 420
	    });
	}
    });
});

$().ready(function () {
    $('div#messages').dialog({
        buttons: { "OK": function () { $(this).dialog("close"); } },
        draggable: false,
        modal: true,
        resizable: false,
        title: 'Admin'
    });
});
