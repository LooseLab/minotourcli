### THIS FILE IS AUTOGENERATED. DO NOT EDIT THIS FILE DIRECTLY ###
from .keystore_pb2_grpc import *
from . import keystore_pb2
from minFQ.rpc.keystore_pb2 import *
from minFQ.rpc._support import MessageWrapper, ArgumentError

__all__ = [
    "KeyStoreService",
    "StoreRequest",
    "StoreResponse",
    "RemoveRequest",
    "RemoveResponse",
    "GetOneRequest",
    "GetOneResponse",
    "GetRequest",
    "GetResponse",
    "WatchRequest",
    "WatchResponse",
    "Lifetime",
    "UNTIL_NEXT_PROTOCOL_START",
    "UNTIL_PROTOCOL_END",
    "UNTIL_INSTANCE_END",
]

class KeyStoreService(object):
    def __init__(self, channel):
        self._stub = KeyStoreServiceStub(channel)
        self._pb = keystore_pb2

    def store(self, _message=None, _timeout=None, **kwargs):
        """
        Store one or more values.

        Anyone watching those values will be notified of the change. If they are watching several of
        the values in a single watch() call, all the updates will be sent in a single message.

        :param values: (required)
            The values to store.

            See the notes in the KeyStore service documentation about names - in short, for any values
            not documented elsewhere, you should be prefixing the name with "<product>:", where <product>
            is the name of your software product.
        :param lifetime:
            Specify the lifetime of a value.

            Note that calling remove() will remove the value regardless of this setting.
        :rtype: StoreResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.store(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = StoreRequest()

        if 'values' in kwargs:
            unused_args.remove('values')
            for key, value in kwargs['values'].items():
                if value.DESCRIPTOR.full_name == 'google.protobuf.Any':
                    _message.values[key].CopyFrom(value)
                else:
                    _message.values[key].Pack(value)
        else:
            raise ArgumentError("store requires a 'values' argument")

        if 'lifetime' in kwargs:
            unused_args.remove('lifetime')
            _message.lifetime = kwargs['lifetime']

        if len(unused_args) > 0:
            raise ArgumentError("store got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.store(_message, timeout=_timeout), unwraps=[])

    def remove(self, _message=None, _timeout=None, **kwargs):
        """
        Remove a value from the store.

        :param names: (required)
            The names of the values you wish to remove.
        :param allow_missing:
            Whether to allow missing values.

            If set, names that are not present in the store will be ignored, but any present values will
            still be removed. Otherwise, missing values will cause an error to be returned (in which case
            nothing will be removed).

            Defaults to 'false'
        :rtype: RemoveResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.remove(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = RemoveRequest()

        if 'names' in kwargs:
            unused_args.remove('names')
            _message.names.extend(kwargs['names'])
        else:
            raise ArgumentError("remove requires a 'names' argument")

        if 'allow_missing' in kwargs:
            unused_args.remove('allow_missing')
            _message.allow_missing = kwargs['allow_missing']

        if len(unused_args) > 0:
            raise ArgumentError("remove got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.remove(_message, timeout=_timeout), unwraps=[])

    def get_one(self, _message=None, _timeout=None, **kwargs):
        """
        Get a single value.

        This is a convenient alternative to get() when you only want a single value. If you want
        multiple values, it is more efficient to request them all in a single get() call.

        If the requested value is not in the store, this will return an error.

        :param name: (required)
            The name of the value to fetch.
        :rtype: GetOneResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_one(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetOneRequest()

        if 'name' in kwargs:
            unused_args.remove('name')
            _message.name = kwargs['name']
        else:
            raise ArgumentError("get_one requires a 'name' argument")

        if len(unused_args) > 0:
            raise ArgumentError("get_one got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_one(_message, timeout=_timeout), unwraps=[])

    def get(self, _message=None, _timeout=None, **kwargs):
        """
        Get any number of values.

        :param names:
            The names of the values you wish to fetch.
        :param allow_missing:
            Whether to allow missing values.

            If set, names that are not present in the store will simply be omitted from the response.
            Otherwise, missing values will cause an error to be returned.

            Defaults to 'false'
        :rtype: GetResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetRequest()

        if 'names' in kwargs:
            unused_args.remove('names')
            _message.names.extend(kwargs['names'])

        if 'allow_missing' in kwargs:
            unused_args.remove('allow_missing')
            _message.allow_missing = kwargs['allow_missing']

        if len(unused_args) > 0:
            raise ArgumentError("get got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get(_message, timeout=_timeout), unwraps=[])

    def watch(self, _message=None, _timeout=None, **kwargs):
        """
        Watch for values being updates.

        On calling this, you will get a message containing the current values, and then messages with
        updates as and when store() is called. The updates will only contain those values that
        changed.

        :param names: (required)
            The names of the values you wish to watch.
        :param allow_missing:
            Whether to allow missing values.

            If set, names that are not present in the store will be omitted from the first response, but
            will still be watched. If and when they are added, a message will be sent with the set
            values. Otherwise, missing values will cause an immediate error.

            Defaults to 'false'
        :rtype: WatchResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.watch(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = WatchRequest()

        if 'names' in kwargs:
            unused_args.remove('names')
            _message.names.extend(kwargs['names'])
        else:
            raise ArgumentError("watch requires a 'names' argument")

        if 'allow_missing' in kwargs:
            unused_args.remove('allow_missing')
            _message.allow_missing = kwargs['allow_missing']

        if len(unused_args) > 0:
            raise ArgumentError("watch got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.watch(_message, timeout=_timeout), unwraps=[])


