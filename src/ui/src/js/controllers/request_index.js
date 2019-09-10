import {formatDate} from '../services/utility_service.js';

requestIndexController.$inject = [
  '$scope',
  '$compile',
  'DTOptionsBuilder',
  'DTColumnBuilder',
  'RequestService',
  'EventService',
];

/**
 * requestIndexController - Angular controller for viewing all requests.
 * @param  {Object} $scope            Angular's $scope object.
 * @param  {Object} DTOptionsBuilder  Data-tables' options builder object.
 * @param  {Object} DTColumnBuilder   Data-tables' column builder object.
 * @param  {Object} RequestService    Beer-Garden Request Service.
 * @param  {Object} EventService      Beer-Garden Event Service.
 */
export default function requestIndexController(
    $scope,
    $compile,
    DTOptionsBuilder,
    DTColumnBuilder,
    RequestService,
    EventService) {
  $scope.setWindowTitle('requests');

  $scope.requests = {};

  $scope.dtOptions = DTOptionsBuilder.newOptions()
    .withOption('autoWidth', false)
    .withOption('ajax', function(data, callback, settings) {
      // Need to also request ID for the href
      data.columns.push({'data': 'id'});

      // Take include_children value from the checkbox
      if ($('#childCheck').is(":checked")) {
        data.include_children = true;
        data.columns.push({'data': 'parent'});
      }

      // Not urlencoding semicolons in the search values breaks the backend
      for (let column of data.columns) {
        if (column.search && column.search.value) {
          column.search.value = column.search.value.replace(/;/g, '%3B');
        }
      }

      RequestService.getRequests(data).then(
        (response) => {
          $scope.response = response;

          callback({
            data: response.data,
            draw: response.headers('draw'),
            recordsFiltered: response.headers('recordsFiltered'),
            recordsTotal: response.headers('recordsTotal'),
          });

          // Hide the 'new data' notification
          $('#newData').css('visibility', 'hidden');
        },
        (response) => {
          $scope.response = response;
        }
      );
    })
    .withLightColumnFilter({
      0: {html: 'input', type: 'text', attr: {class: 'form-inline form-control'}},
      1: {html: 'input', type: 'text', attr: {class: 'form-inline form-control'}},
      2: {html: 'input', type: 'text', attr: {class: 'form-inline form-control'}},
      3: {
        html: 'select',
        type: 'text',
        cssClass: 'form-inline form-control',
        values: [
          {value: '', label: ''},
          {value: 'CREATED', label: 'CREATED'},
          {value: 'RECEIVED', label: 'RECEIVED'},
          {value: 'IN_PROGRESS', label: 'IN PROGRESS'},
          {value: 'CANCELED', label: 'CANCELED'},
          {value: 'SUCCESS', label: 'SUCCESS'},
          {value: 'ERROR', label: 'ERROR'},
        ],
      },
      4: {
        html: 'range',
        type: 'text',
        attr: {
          class: 'form-inline form-control w-50',
        },
        startAttr: {
          placeholder: 'start',
        },
        endAttr: {
          placeholder: 'end',
        },
        picker: {
          format: 'YYYY-MM-DD HH:mm:ss',
          showClear: true,
          showTodayButton: true,
          useCurrent: false,
        },
      },
      5: {html: 'input', type: 'text', attr: {class: 'form-inline form-control'}},
    })
    .withDataProp('data')
    .withOption('order', [4, 'desc'])
    .withOption('serverSide', true)
    .withOption('refreshButton', true)
    .withOption('childContainer', true)
    .withOption('newData', true)
    .withPaginationType('full_numbers')
    .withBootstrap()
    .withOption('createdRow', function(row, data, dataIndex) {
      $compile(angular.element(row).contents())($scope);
    });

  $scope.dtColumns = [
    DTColumnBuilder
      .newColumn('command')
      .withTitle('Command Name')
      .renderWith(function(data, type, full) {
        let display = '';

        if (full.parent) {
          display +=
            '<span style="margin-right: 2px;"' +
              `uib-popover="${full.parent.command}"` +
              'popover-trigger="\'mouseenter\'"' +
              'popover-title="parent request"' +
              'popover-animation="true"' +
              'popover-placement="left">' +
                `<a ui-sref="base.namespace.request({requestId: '${full.parent.id}'})" ` +
                  'class="fa fa-level-up fa-fw">' +
                '</a>' +
            '</span>';
        }

        return display + `<a ui-sref="base.namespace.request({requestId: '${full.id}'})">` + data + '</a>';
      }),
    DTColumnBuilder
      .newColumn('system')
      .withTitle('System')
      .renderWith(function(data, type, full) {
        let systemName = data;
        if (full['metadata'] && full['metadata']['system_display_name']) {
          systemName = full['metadata']['system_display_name'];
        }
        return systemName;
      }),
    DTColumnBuilder
      .newColumn('instance_name')
      .withTitle('Instance'),
    DTColumnBuilder
      .newColumn('status')
      .withTitle('Status'),
    DTColumnBuilder
      .newColumn('created_at')
      .withTitle('Created')
      .withOption('type', 'date')
      .withOption('width', '25%')
      .renderWith(function(data, type, full) {
        return formatDate(data);
      }),
    DTColumnBuilder
      .newColumn('comment')
      .withTitle('Comment'),
    DTColumnBuilder
      .newColumn('metadata')
      .notVisible(),
  ];

  $scope.instanceCreated = function(_instance) {
    $scope.dtInstance = _instance;
  };

  EventService.addCallback('request_index', (event) => {
    switch (event.name) {
      case 'REQUEST_CREATED':
      case 'REQUEST_STARTED':
      case 'REQUEST_COMPLETED':
        if ($scope.dtInstance) {
          $('#newData').css('visibility', 'visible');
        }
        break;
    }
  });

  $scope.$on('$destroy', function() {
    EventService.removeCallback('request_index');
  });

  $scope.$on('userChange', function() {
    $scope.response = undefined;

    if ($scope.dtInstance) {
      $scope.dtInstance.reloadData(() => {}, false);
    }
  });
};