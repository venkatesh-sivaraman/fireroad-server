
var graphBackgroundColors = [
  'rgba(227, 59, 59, 0.4)',
  'rgba(73, 29, 180, 0.4)',
  'rgba(4, 223, 217, 0.4)',
  'rgba(5, 154, 20, 0.4)',
  'rgba(201, 27, 121, 0.4)'
];

var graphBorderColors = [
  'rgba(227, 59, 59, 1.0)',
  'rgba(73, 29, 180, 1.0)',
  'rgba(4, 223, 217, 1.0)',
  'rgba(5, 154, 20, 1.0)',
  'rgba(201, 27, 121, 1.0)'
];

$.ajax({
  url: "/analytics/total_requests/",
  data: null,
  success: function (result) {
    var ctx = document.getElementById('total-requests-chart').getContext('2d');
    var myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: result.labels,
            datasets: [{
              label: '# of Requests',
              data: result.data,
              backgroundColor: graphBackgroundColors[0],
              borderColor: graphBorderColors[0],
              borderWidth: 1
            }]
        },
        options: {
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true
                    }
                }],
                xAxes: [{
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 10
                    }
                }]
            },
            aspectRatio: 1.6
        }
    });
  }
});

$.ajax({
  url: "/analytics/user_agents/",
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
    var myChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: result.labels,
            datasets: datasets
        },
        options: {
            scales: {
                yAxes: [{
                    ticks: {
                        beginAtZero: true
                    },
                    stacked: true
                }],
                xAxes: [{
                    ticks: {
                        autoSkip: true,
                        maxTicksLimit: 10
                    },
                    stacked: true
                }]
            },
            aspectRatio: 1.6
        }
    });
  }
});
