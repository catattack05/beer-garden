# -*- coding: utf-8 -*-
import asyncio
import copy
import json
from concurrent.futures.thread import ThreadPoolExecutor
from functools import partial

import six
from brewtils.models import (
    System,
    Instance,
    Command,
    Parameter,
    Request,
    PatchOperation,
    LoggingConfig,
    Event,
    Queue,
    Principal,
    Role,
    RefreshToken,
    Job,
)
from brewtils.schema_parser import SchemaParser

import beer_garden.api


class ExecutorClient(object):
    parser = SchemaParser()
    pool = ThreadPoolExecutor(50)

    def __getattr__(self, _api):
        return partial(self, _api)

    async def __call__(self, *args, serialize_kwargs=None, **kwargs):
        result = await asyncio.get_event_loop().run_in_executor(
            self.pool, partial(getattr(beer_garden.api, args[0]), *args[1:], **kwargs)
        )

        return self.serialize(result, **(serialize_kwargs or {}))

    # TODO - This really needs to be handled by the Parser subsystem
    @classmethod
    def serialize(cls, model, to_string=True, **kwargs):
        """Convenience method to serialize any model type

        Args:
            model: The model object(s) to serialize
            to_string: True generates a JSON-formatted string, False generates a dict
            **kwargs: Additional parameters to be passed to the Schema (e.g. many=True)

        Returns:
            A string or dict representation of the model object. Which depends on the
            value of the to_string parameter.

        """
        if isinstance(model, (six.string_types, dict)):
            return model
        elif isinstance(model, System):
            return cls.parser.serialize_system(model, to_string=to_string, **kwargs)
        elif isinstance(model, Instance):
            return cls.parser.serialize_instance(model, to_string=to_string, **kwargs)
        elif isinstance(model, Command):
            return cls.parser.serialize_command(model, to_string=to_string, **kwargs)
        elif isinstance(model, Parameter):
            return cls.parser.serialize_parameter(model, to_string=to_string, **kwargs)
        elif isinstance(model, Request):
            return cls.parser.serialize_request(model, to_string=to_string, **kwargs)
        elif isinstance(model, PatchOperation):
            return cls.parser.serialize_patch(model, to_string=to_string, **kwargs)
        elif isinstance(model, LoggingConfig):
            return cls.parser.serialize_logging_config(
                model, to_string=to_string, **kwargs
            )
        elif isinstance(model, Event):
            return cls.parser.serialize_event(model, to_string=to_string, **kwargs)
        elif isinstance(model, Queue):
            return cls.parser.serialize_queue(model, to_string=to_string, **kwargs)
        elif isinstance(model, Principal):
            return cls.parser.serialize_principal(model, to_string=to_string, **kwargs)
        elif isinstance(model, Role):
            return cls.parser.serialize_role(model, to_string=to_string, **kwargs)
        elif isinstance(model, RefreshToken):
            return cls.parser.serialize_refresh_token(
                model, to_string=to_string, **kwargs
            )
        elif isinstance(model, Job):
            return cls.parser.serialize_job(model, to_string=to_string, **kwargs)
        elif isinstance(model, list):
            nested_kwargs = copy.copy(kwargs)
            nested_kwargs["to_string"] = False
            nested_kwargs["many"] = False

            serialized = [cls.serialize(x, **nested_kwargs) for x in model]

            return json.dumps(serialized) if to_string else serialized

        raise ValueError("Unable to determine model type")