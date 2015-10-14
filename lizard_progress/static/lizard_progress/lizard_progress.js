// (c) Nelen & Schuurmans.  GPL licensed, see LICENSE.txt.

// jslint configuration
/*global $, map */

// Upload popup
$().ready(function () {
    var $dialog, url;

    url = $('#upload-wrapper').attr('data-upload-dialog-url');

    on_open = function() {
        var uploader = uploader || $('#uploader').plupload('getUploader');
        //Next line seems to solve a problem with the "Add Files"
        //button in Chrome when using a modal dialog.
        $('#uploader > div.plupload').css('z-index','99999');
        uploader.settings.url = $(this).attr('data-upload-url');
        uploader.splice(); // Clean the queue
        uploader.refresh();
    };

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

        // Simple upload form for IE
        $simple_form = $('#simple-upload-form');
        $simple_form.attr("action", $(this).attr('data-upload-url'));

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
        title: 'Melding',
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

        // Disable this button
        $(this).attr('disabled', 'disabled');

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

// Make table rows clickable
$("tr.clickable").click(function (event) {
    event.preventDefault();
    url = $(this).attr('data-url');

    if (url) {
        window.location = url;
    }
});

// Or table cells (URL is still in the tr)
$("td.clickable").click(function (event) {
    event.preventDefault();
    url = $(this).closest("tr").attr("data-url");

    if (url) {
        window.location = url;
    }
});

// Deleting uploaded files using a clickable link
$("a.delete_file").click(function (event) {
    event.preventDefault();
    if (confirm($(this).attr("data-message"))) {
        // Send DELE to the file's download URL
        $.ajax({
            url: $(this).attr("href"),
            type: 'DELETE',
            success: function () {
                location.reload(true);
            }
        });
    }
});

// A button that redirects to some page
$("button.redirect").click(function (event) {
    console.log(event);
    event.preventDefault();
    var url = $(this).attr("data-redirect-url");
    if (url) {
        window.location.href = url;
    }
});

// A button to archive a project
$("#bt-archive").click(function (event) {
    var msg = "";
    if (this.name == "archive"){
	msg = "Project wordt gearchiveerd. Weet u het zeker?";
    } else {
	msg = "Project wordt geactiveerd. Weet u het zeker?";
    }

    if (confirm(msg)){
	window.location = this.value;
    }
});

$(function () {
    $('.tree li:has(ul)').addClass('parent_li').find(' > span').attr('title', 'Collapse this branch');
    $('.tree li.parent_li > span').on('click', function (e) {
        var children = $(this).parent('li.parent_li').find(' > ul > li');
        if (children.is(":visible")) {
            children.hide('fast');
            $(this).attr('title', 'Expand this branch').find(' > i').addClass('icon-plus-sign').removeClass('icon-minus-sign');
        } else {
            children.show('fast');
            $(this).attr('title', 'Collapse this branch').find(' > i').addClass('icon-minus-sign').removeClass('icon-plus-sign');
        }
        e.stopPropagation();
    });
});

// Click away closed requests on the changerequests page
$("button.close").click(function (event) {
    event.preventDefault();
    var url = $(this).attr("data-post-url");
    if (url) {
        $.ajax({
            url: url,
            type: 'POST'
        });
    }
    // Hide table row, if any
    var $tr = $(this).closest('tr');
    $tr.hide();
});

// Submit a form Ajax-style. Find out which button was pressed, in
// which form the button is, set a hidden field pointed at by the
// button, then submit the form.
var ajax_submit = function (button) {
    var $button = $(button);

    var $hidden = $($button.attr("data-hidden-id"));

    var $form = $button.closest('form');
    var formdata = $form.serialize();

    if ($hidden) {
        $hidden.attr("value", $hidden.attr("name"));
        formdata = $form.serialize();
        $hidden.attr("value", "");
    }

    var url = $form.attr("action");

    $.post(url, formdata,function (data) {
        if (data.success) {
            // Reload page? Easiest way to close the dialog, delete the
            // request from the sidebar, and stop showing the request on
            // the map.
            location.reload();
        } else {
            var error_span_id = data.error_span_id || "#submit-errors";
            var $errors = $(error_span_id);
            $errors.html(data.error);
        }
    });
};
