var previewMode = 0;

function onPreviewButtonClicked(editTitle, textSelector, editorSelector) {
  if (previewMode == 0) {
    // Go to preview
    $("#preview-button").text(editTitle);
    $("#preview-loading-ind").addClass("active");
    previewMode = 1;
    $.ajax({
      url: "/requirements/preview/",
      type: "POST",
      data: $(textSelector).val(),
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
  $(editorSelector).toggle();
}
