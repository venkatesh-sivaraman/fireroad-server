var previewMode = 0;

function onPreviewButtonClicked() {
  if (previewMode == 0) {
    // Go to preview
    $("#preview-button").text("Edit");
    $("#preview-loading-ind").addClass("active");
    previewMode = 1;
    $.ajax({
      url: "/requirements/preview/",
      type: "POST",
      data: $("#contents").val(),
      contentType:"text/plain; charset=utf-8",
      success: function(data) {
        $("#preview").html(data);
        $("#preview").toggle();
        $("#preview-loading-ind").removeClass("active");
      }
    });

  } else {
    // Go back to edit
    $("#preview-button").text("Preview");
    previewMode = 0;
    $("#preview").toggle();
  }
  $("#contents").toggle();
}
