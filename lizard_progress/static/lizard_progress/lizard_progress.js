// (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

// jslint configuration
/*global $, map */

// Upload popup
$().ready(function () {
    var $dialog, url;

    url = $('#upload-wrapper').attr('data-upload-dialog-url');

    // Preload
    $dialog = $('<div class="lizard-progress-popup"/>').load(url).dialog({
        autoOpen: false,
        //The "Add Files" button does not work in Chrome when
        //using a modal dialog. This is a z-index bug?
        //modal: true,
        title: 'Uploaden',
        width: 500
    });

    var uploader;

    $('.upload').click(function () {
        $dialog.dialog('open');
        uploader = uploader || $('#uploader').plupload('getUploader');
        //Next line seems to solve a problem with the "Add Files"
        //button in Chrome when using a modal dialog.
        //$('#uploader > div.plupload').css('z-index','99999');
        uploader.settings.url = $(this).attr('data-upload-url');
        uploader.splice(); // Clean the queue
        uploader.refresh();

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
        var location_code = $(this).attr('data-location-code');
        var measurement_type = $(this).attr('data-measurement-type');

        var dialog_key = comparison_url + location_code;

        if (dialogs[dialog_key]) {
            dialogs[dialog_key].dialog('open');
        } else {
            dialogs[dialog_key] = $('<div class="lizard-progress-popup"/>').dialog({
                autoOpen: true,
                open: function(event, ui) {
                    $(this).load(comparison_url);
                },
                title: 'Vergelijking '+measurement_type+' Locatie '+location_code,
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
        title: 'Admin',
        width: 450
    });
});

$().ready(function () {
    $('.tooltip').click(function () {
        // prevent the default action, e.g., following a link
        return false;
    });
    $('.legend-tooltip').click(function () {
        // prevent the default action, e.g., following a link
        return false;
    });
});

$().ready(function () {
    $(".export-run-button").click(function () {
        var export_run_id = $(this).attr('data-export-run-id');
        var post_to_url = $(this).attr('data-export-run-url');
        var loader_gif = $(this).attr('data-loader-gif');

        // Clear relevant table cells
        $("td#present-" + export_run_id).html(
            "<img src=\"" + loader_gif + "\">");
        $("td#uptodate-" + export_run_id).html("");
        $("td#download-" + export_run_id).html("");

        // Post to url
        $.post(post_to_url);

        // Reload page after 1 sec
        setTimeout(function () {
            location.reload();
        }, 1000);
    });
});

$().ready(function () {
    // If there is a table row with class "please-reload-me", reload
    // the page after 1 second.
    if ($("tr.please-reload-me").length > 0) {
        // Reload page after 1 sec
        setTimeout(function () {
            location.reload();
        }, 1000);
    }
});
