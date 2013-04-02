var upload_page_functions = upload_page_functions || (function () {
    var id_not_ready_div = "#uploaded_files_not_ready";
    var id_ready_div = "#uploaded_files_ready";

    var make_row_id = function (uploaded_file) {
        if (uploaded_file.ready) {
            return "uploaded-file-ready-" + uploaded_file.id;
        } else {
            return "uploaded-file-not-ready-" + uploaded_file.id;
        }
    };

    var add_to_ready_table = function (uploaded_file) {
        $(id_ready_div + " table").append(
            $("<tr>")
                  .attr("id", make_row_id(uploaded_file))
                  .attr("class", uploaded_file.success ? "success" : "error")
                  .append($("<td>").append(uploaded_file.filename))
                  .append($("<td>").append(uploaded_file.uploaded_by))
                  .append($("<td>").append(uploaded_file.uploaded_at))
                  .append($("<td>").append(
                      uploaded_file.success ? "" :
                            ($("<a>").attr("href", uploaded_file.error_url)
                            .attr("target", "_")
                             .text("bekijk fouten"))))
                  .append($("<td>").append(
                      $("<a>").attr("href", uploaded_file.delete_url)
                            .attr("class", "delete-uploaded-file")
                            .text("verwijder")))
        );
        $(id_ready_div).fadeIn();
    };

    var add_to_unready_table = function (uploaded_file) {
        $(id_not_ready_div + " table").append(
            $("<tr>")
                  .attr("id", make_row_id(uploaded_file))
                  .append($("<td>").append(uploaded_file.filename))
                  .append($("<td>").append(uploaded_file.uploaded_by))
                  .append($("<td>").append(uploaded_file.uploaded_at))
        );
        $(id_not_ready_div).fadeIn();
    }

    var refresh_uploaded_file_tables = function () {
        refresh_url = $(id_not_ready_div).attr("data-refresh-url");

        $.getJSON(refresh_url, function (data) {
            var ids_to_keep = {};

            // Sync our tables to the ids in the data
            // First we go to the data, adding any rows not present yet,
            // and adding all ids to ids_to_keep.
            // Then we go through all table rows and remove the links
            // we shouldn't keep anymore.

            $.each(data, function(i, uploaded_file) {
                var row_id = make_row_id(uploaded_file);
                ids_to_keep[row_id] = true;

                if ($("#"+row_id).length == 0) {
                    if (uploaded_file.ready) {
                        add_to_ready_table(uploaded_file);
                    } else {
                        add_to_unready_table(uploaded_file);
                    }
                }
            });

            $(".uploadedfiletable tbody tr").each(function (i, row) {
                row = $(row);
                if (!(row.attr("id") in ids_to_keep)) {
                    row.remove();
                }
            });

            if ($(id_not_ready_div + " table tbody tr").length == 0) {
                $(id_not_ready_div).fadeOut();
            } else {
                // Keep refreshing until this table is empty
                setTimeout(refresh_uploaded_file_tables, 1000);
            }

            if ($(id_ready_div + " table tbody tr").length == 0) {
                $(id_ready_div).fadeOut();
            }
        });
    };

    var delete_uploaded_file = function() {
        row = $(this).closest("tr");
        url = $(this).attr("href");

        $.post(url);
        row.remove();
        setTimeout(refresh_uploaded_file_tables, 500);

        return false;
    };

    return {
        refresh_uploaded_file_tables: refresh_uploaded_file_tables,
        delete_uploaded_file: delete_uploaded_file
    };
})();

$(upload_page_functions.refresh_uploaded_file_tables);
$(document).on("click", "a.delete-uploaded-file", upload_page_functions.delete_uploaded_file);
