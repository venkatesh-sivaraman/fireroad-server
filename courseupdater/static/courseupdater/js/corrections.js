$(document).ready(function() {
  $.ajax({
            url: '/courses/all',
            type: 'get',
            cache: false,
            success: function (data) {
              var courses = {};
              for (item in data) {
                courses[data[item].subject_id] = null;
              }
              $('input.autocomplete').autocomplete("updateData", courses);
            },
            error: function (err) {
                console.log(err);
            }
        });
  $('input.autocomplete').autocomplete({
    data: {},
    limit: 10,
    minLength: 1, // The minimum length of the input for the autocomplete to start. Default: 1.
  });
});
