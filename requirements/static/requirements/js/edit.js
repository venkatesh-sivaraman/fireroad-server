var previewMode = 0;

function onPreviewButtonClicked() {
  if (previewMode == 0) {
    // Go to preview
    $("#preview-button").text("Edit");
    previewMode = 1;
    $.ajax({
      url: "/requirements/preview/",
      type: "POST",
      data: $("#contents").val(),
      contentType:"text/plain; charset=utf-8",
      success: function(data) {
        $("#preview").html(data);
      }
    });

  } else {
    // Go back to edit
    $("#preview-button").text("Preview");
    previewMode = 0;
  }
  $("#contents").toggle();
  $("#preview").toggle();
}
