
var graphBackgroundColors = [
  'rgba(142, 8, 48, 0.4)',
  'rgba(143, 9, 105, 0.4)',
  'rgba(227, 59, 59, 0.4)',
  'rgba(201, 27, 121, 0.4)',
  'rgba(77, 8, 177, 0.4)',
];

var graphBorderColors = [
  'rgba(142, 8, 48, 1)',
  'rgba(143, 9, 105, 1.0)',
  'rgba(227, 59, 59, 1.0)',
  'rgba(201, 27, 121, 1.0)',
  'rgba(77, 8, 177, 1.0)',
];

var timeframe = "day";

var totalRequestsChart = null;
var userAgentsChart = null;
var loggedInUsersChart = null;
var semestersChart = null;
var requestPathsChart = null;

function makeBarChartOptions(show_all) {
  return {
    scales: {
      yAxes: [{
        ticks: {
          beginAtZero: true
        },
        stacked: true,
      }],
      xAxes: [{
        ticks: show_all ? {} : {
          autoSkip: true,
          maxTicksLimit: 10
        },
        barPercentage: 1.0,
        stacked: true,
      }]
    },
    aspectRatio: 1.6
  }
}

// Reloads the data from the server with a specific time frame.
function reloadData() {
  $.ajax({
    url: "/analytics/total_requests/" + timeframe,
    data: null,
    success: function (result) {
      var ctx = document.getElementById('total-requests-chart').getContext('2d');
      var data = {
        labels: result.labels,
        datasets: [{
          label: '# of Requests',
          data: result.data,
          backgroundColor: graphBackgroundColors[0],
          borderColor: graphBorderColors[0],
          borderWidth: 1
        }]
      }
      if (!totalRequestsChart) {
        totalRequestsChart = new Chart(ctx, {
          type: 'bar',
          data: data,
          options: makeBarChartOptions(false)
        });
      } else {
        totalRequestsChart.data = data;
        totalRequestsChart.update();
      }
    }
  });

  $.ajax({
    url: "/analytics/logged_in_users/" + timeframe,
    data: null,
    success: function (result) {
      var ctx = document.getElementById('unique-users-chart').getContext('2d');
      var data = {
        labels: result.labels,
        datasets: [{
          label: 'Unique Users',
          data: result.data,
          backgroundColor: graphBackgroundColors[0],
          borderColor: graphBorderColors[0],
          borderWidth: 1
        }]
      }
      if (!loggedInUsersChart) {
        loggedInUsersChart = new Chart(ctx, {
          type: 'bar',
          data: data,
          options: makeBarChartOptions(false)
        });
      } else {
        loggedInUsersChart.data = data;
        loggedInUsersChart.update();
      }
    }
  });

  $.ajax({
    url: "/analytics/user_agents/" + timeframe,
    data: null,
    success: function (result) {
      var ctx = document.getElementById('user-agents-chart').getContext('2d');
      var datasets = [];
      var i = 0;
      for (var key in result.data) {
        if (!result.data.hasOwnProperty(key)) {
          continue;
        }
        datasets.push({
          label: key,
          data: result.data[key],
          backgroundColor: graphBackgroundColors[i % graphBackgroundColors.length],
          borderColor: graphBorderColors[i % graphBorderColors.length],
          borderWidth: 1
        })
        i++;
      }
      var data = {
          labels: result.labels,
          datasets: datasets
      }
      if (!userAgentsChart) {
        userAgentsChart = new Chart(ctx, {
          type: 'bar',
          data: data,
          options: makeBarChartOptions(false)
        });
      } else {
        userAgentsChart.data = data;
        userAgentsChart.update();
      }
    }
  });

  $.ajax({
    url: "/analytics/user_semesters/" + timeframe,
    data: null,
    success: function (result) {
      var ctx = document.getElementById('user-semesters-chart').getContext('2d');
      var data = {
          labels: result.labels,
          datasets: [{
            label: "# of Users",
            data: result.data,
            backgroundColor: graphBackgroundColors[0],
            borderColor: graphBorderColors[0],
            borderWidth: 1
          }]
      }
      if (!semestersChart) {
        semestersChart = new Chart(ctx, {
          type: 'bar',
          data: data,
          options: makeBarChartOptions(true)
        });
      } else {
        semestersChart.data = data;
        semestersChart.update();
      }
    }
  });

  $.ajax({
    url: "/analytics/request_paths/" + timeframe,
    data: null,
    success: function (result) {
      var ctx = document.getElementById('request-paths-chart').getContext('2d');
      var data = {
          labels: result.labels,
          datasets: [{
            label: "# of Requests",
            data: result.data,
            backgroundColor: graphBackgroundColors[0],
            borderColor: graphBorderColors[0],
            borderWidth: 1
          }]
      }
      if (!requestPathsChart) {
        requestPathsChart = new Chart(ctx, {
          type: 'bar',
          data: data,
          options: makeBarChartOptions(true)
        });
      } else {
        requestPathsChart.data = data;
        requestPathsChart.update();
      }
    }
  });
}

// Initialize the time frame selector
$(document).ready(function(){
   $('select').formSelect();
});
reloadData();

function timeframeChanged() {
  timeframe = $('#timeframe-select').val();
  reloadData();
}
