$(function () {
    var checkbox = $("#toggle-success-line");

    checkbox.click(function (e) {
        state = $(this).attr("checked");

        $("tr.successline").css(
            "display",
            state ? "" : "none");
    });
});
