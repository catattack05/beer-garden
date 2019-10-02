# -*- coding: utf-8 -*-
from brewtils.schema_parser import SchemaParser
from brewtils.schemas import SystemSchema

from beer_garden.api.http.authorization import authenticated, Permissions
from beer_garden.api.http.base_handler import BaseHandler


class SystemAPI(BaseHandler):
    @authenticated(permissions=[Permissions.SYSTEM_READ])
    async def get(self, system_id):
        """
        ---
        summary: Retrieve a specific System
        parameters:
          - name: bg-namespace
            in: header
            required: false
            description: Namespace to use
            type: string
          - name: system_id
            in: path
            required: true
            description: The ID of the System
            type: string
          - name: include_commands
            in: query
            required: false
            description: Include the System's commands in the response
            type: boolean
            default: true
        responses:
          200:
            description: System with the given ID
            schema:
              $ref: '#/definitions/System'
          404:
            $ref: '#/definitions/404Error'
          50x:
            $ref: '#/definitions/50xError'
        tags:
          - Systems
        """
        # TODO - This is part of the v1 API, need to work this back in
        # include_commands = (
        #     self.get_query_argument("include_commands", default="").lower() != "false"
        # )

        response = await self.client.get_system(self.request.namespace, system_id)

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(response)

    @authenticated(permissions=[Permissions.SYSTEM_DELETE])
    async def delete(self, system_id):
        """
        Will give Bartender a chance to remove instances of this system from the
        registry but will always delete the system regardless of whether the Bartender
        operation succeeds.
        ---
        summary: Delete a specific System
        description: Will remove instances of local plugins from the registry, clear
            and remove message queues, and remove the system from the database.
        parameters:
          - name: bg-namespace
            in: header
            required: false
            description: Namespace to use
            type: string
          - name: system_id
            in: path
            required: true
            description: The ID of the System
            type: string
        responses:
          204:
            description: System has been successfully deleted
          404:
            $ref: '#/definitions/404Error'
          50x:
            $ref: '#/definitions/50xError'
        tags:
          - Systems
        """
        await self.client.remove_system(self.request.namespace, system_id)

        self.set_status(204)

    @authenticated(permissions=[Permissions.SYSTEM_UPDATE])
    async def patch(self, system_id):
        """
        ---
        summary: Partially update a System
        description: |
          The body of the request needs to contain a set of instructions detailing the
          updates to apply.
          Currently supported operations are below:
          ```JSON
          {
            "operations": [
              { "operation": "add", "path": "/instance", "value": "" },
              { "operation": "replace", "path": "/commands", "value": "" },
              { "operation": "replace", "path": "/description", "value": "new description"},
              { "operation": "replace", "path": "/display_name", "value": "new display name"},
              { "operation": "replace", "path": "/icon_name", "value": "new icon name"},
              { "operation": "update", "path": "/metadata", "value": {"foo": "bar"}}
            ]
          }
          ```
          Where `value` is a list of new Commands.
        parameters:
          - name: bg-namespace
            in: header
            required: false
            description: Namespace to use
            type: string
          - name: system_id
            in: path
            required: true
            description: The ID of the System
            type: string
          - name: patch
            in: body
            required: true
            description: Instructions for how to update the System
            schema:
              $ref: '#/definitions/Patch'
        responses:
          200:
            description: System with the given ID
            schema:
              $ref: '#/definitions/System'
          400:
            $ref: '#/definitions/400Error'
          404:
            $ref: '#/definitions/404Error'
          50x:
            $ref: '#/definitions/50xError'
        tags:
          - Systems
        """
        response = await self.client.update_system(
            self.request.namespace,
            system_id,
            SchemaParser.parse_patch(self.request.decoded_body, from_string=True),
        )

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(response)


class SystemListAPI(BaseHandler):

    REQUEST_FIELDS = set(SystemSchema.get_attribute_names())

    @authenticated(permissions=[Permissions.SYSTEM_READ])
    async def get(self):
        """
        ---
        summary: Retrieve all Systems
        description: |
          This endpoint allows for querying Systems.

          There are several parameters that control which fields are returned
          and what information is available. Things to be aware of:

          * The `include_commands` parameter is __deprecated__. Don't use it.
            Use `exclude_fields=commands` instead.

          * It's possible to specify `include_fields` _and_ `exclude_fields`.
            This doesn't make a lot of sense, but you can do it. If the same
            field is in both `exclude_fields` takes priority (the field will
            NOT be included in the response).

          Systems matching specific criteria can be filtered using additional
          query parameters. This is a very basic capability:

          * ?name=foo&version=1.0.0
            This will return the system named 'foo' with version '1.0.0'
          * ?name=foo&name=bar
            This will not do what you expect: only return the system named
            'bar' will be returned.
        parameters:
          - name: bg-namespace
            in: header
            required: false
            description: Namespace to use
            type: string
          - name: include_fields
            in: query
            required: false
            description: Specify fields to include in the response. All other
              fields will be excluded.
            type: array
            collectionFormat: csv
            items:
              type: string
          - name: exclude_fields
            in: query
            required: false
            description: Specify fields to exclude from the response
            type: array
            collectionFormat: csv
            items:
              type: string
          - name: dereference_nested
            in: query
            required: false
            description: Commands and instances will be an object id
            type: boolean
            default: true
        responses:
          200:
            description: All Systems
            schema:
              type: array
              items:
                $ref: '#/definitions/System'
          50x:
            $ref: '#/definitions/50xError'
        tags:
          - Systems
        """
        order_by = self.get_query_argument("order_by", None)

        dereference_nested = self.get_query_argument("dereference_nested", None)
        if dereference_nested is None:
            dereference_nested = True
        else:
            dereference_nested = bool(dereference_nested.lower() == "true")

        include_fields = self.get_query_argument("include_fields", None)
        if include_fields:
            include_fields = set(include_fields.split(",")) & self.REQUEST_FIELDS

        exclude_fields = self.get_query_argument("exclude_fields", None)
        if exclude_fields:
            exclude_fields = set(exclude_fields.split(",")) & self.REQUEST_FIELDS

        # TODO - Handle multiple query arguments with the same key
        # for example: (?name=foo&name=bar) ... what should that mean?
        # Need to use self.request.query_arguments to get all the query args
        filter_params = {}
        for key in self.request.query_arguments:
            if key in self.REQUEST_FIELDS:
                filter_params[key] = self.get_query_argument(key)

        serialize_kwargs = {"to_string": True, "many": True}
        if include_fields:
            serialize_kwargs["only"] = include_fields
        if exclude_fields:
            serialize_kwargs["exclude"] = exclude_fields

        response = await self.client.get_systems(
            self.request.namespace,
            serialize_kwargs=serialize_kwargs,
            filter_params=filter_params,
            order_by=order_by,
            include_fields=include_fields,
            exclude_fields=exclude_fields,
            dereference_nested=dereference_nested,
        )

        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(response)

    @authenticated(permissions=[Permissions.SYSTEM_CREATE])
    async def post(self):
        """
        ---
        summary: Create a new System or update an existing System
        description: |
            If the System does not exist it will be created. If the System
            already exists it will be updated (assuming it passes validation).
        parameters:
          - name: bg-namespace
            in: header
            required: false
            description: Namespace to use
            type: string
          - name: system
            in: body
            description: The System definition to create / update
            schema:
              $ref: '#/definitions/System'
        responses:
          200:
            description: An existing System has been updated
            schema:
              $ref: '#/definitions/System'
          201:
            description: A new System has been created
            schema:
              $ref: '#/definitions/System'
          400:
            $ref: '#/definitions/400Error'
          50x:
            $ref: '#/definitions/50xError'
        tags:
          - Systems
        """
        response = await self.client.create_system(
            self.request.namespace,
            SchemaParser.parse_system(self.request.decoded_body, from_string=True),
        )

        self.set_status(201)
        self.set_header("Content-Type", "application/json; charset=UTF-8")
        self.write(response)