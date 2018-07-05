# Generated by the protocol buffer compiler.  DO NOT EDIT!
# source: minknow/rpc/production.proto

import sys
_b=sys.version_info[0]<3 and (lambda x:x) or (lambda x:x.encode('latin1'))
from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database
from google.protobuf import descriptor_pb2
# @@protoc_insertion_point(imports)

_sym_db = _symbol_database.Default()




DESCRIPTOR = _descriptor.FileDescriptor(
  name='minknow/rpc/production.proto',
  package='ont.rpc.production',
  syntax='proto3',
  serialized_pb=_b('\n\x1cminknow/rpc/production.proto\x12\x12ont.rpc.production\"\xfc\x05\n\x18WriteFlowcellDataRequest\x12\x43\n\x05\x65mpty\x18\x01 \x01(\x0b\x32\x32.ont.rpc.production.WriteFlowcellDataRequest.EmptyH\x00\x12\x43\n\x02v1\x18\x02 \x01(\x0b\x32\x35.ont.rpc.production.WriteFlowcellDataRequest.Version1H\x00\x12\x43\n\x02v2\x18\x03 \x01(\x0b\x32\x35.ont.rpc.production.WriteFlowcellDataRequest.Version2H\x00\x12\x43\n\x02v3\x18\x04 \x01(\x0b\x32\x35.ont.rpc.production.WriteFlowcellDataRequest.Version3H\x00\x12\x43\n\x02v4\x18\x05 \x01(\x0b\x32\x35.ont.rpc.production.WriteFlowcellDataRequest.Version4H\x00\x1a\x07\n\x05\x45mpty\x1a\x1f\n\x08Version1\x12\x13\n\x0b\x66lowcell_id\x18\x01 \x01(\t\x1a:\n\x08Version2\x12\x19\n\x11wells_per_channel\x18\x01 \x01(\r\x12\x13\n\x0b\x66lowcell_id\x18\x02 \x01(\t\x1a\xa4\x01\n\x08Version3\x12\x15\n\rminor_version\x18\x01 \x01(\r\x12\x19\n\x11wells_per_channel\x18\x02 \x01(\r\x12\x1c\n\x12temperature_offset\x18\x03 \x01(\x11H\x00\x12\x13\n\x0b\x66lowcell_id\x18\x04 \x01(\t\x12\x14\n\x0cproduct_code\x18\x05 \x01(\tB\x1d\n\x1btemperature_offset_nullable\x1ar\n\x08Version4\x12\x15\n\rminor_version\x18\x01 \x01(\r\x12\x1c\n\x12temperature_offset\x18\x02 \x01(\x11H\x00\x12\x12\n\nadapter_id\x18\x03 \x01(\tB\x1d\n\x1btemperature_offset_nullableB\x06\n\x04\x64\x61ta\"\x1b\n\x19WriteFlowcellDataResponse\"-\n\x16WriteFlowcellIdRequest\x12\x13\n\x0b\x66lowcell_id\x18\x01 \x01(\t\"\x19\n\x17WriteFlowcellIdResponse\"8\n\x1bWriteWellsPerChannelRequest\x12\x19\n\x11wells_per_channel\x18\x01 \x01(\r\"\x1e\n\x1cWriteWellsPerChannelResponse\"/\n\x17WriteProductCodeRequest\x12\x14\n\x0cproduct_code\x18\x01 \x01(\t\"\x1a\n\x18WriteProductCodeResponse\"D\n\x1dWriteTemperatureOffsetRequest\x12\x10\n\x06offset\x18\x01 \x01(\x05H\x00\x42\x11\n\x0foffset_nullable\" \n\x1eWriteTemperatureOffsetResponse2\xf2\x04\n\x11ProductionService\x12t\n\x13write_flowcell_data\x12,.ont.rpc.production.WriteFlowcellDataRequest\x1a-.ont.rpc.production.WriteFlowcellDataResponse\"\x00\x12n\n\x11write_flowcell_id\x12*.ont.rpc.production.WriteFlowcellIdRequest\x1a+.ont.rpc.production.WriteFlowcellIdResponse\"\x00\x12~\n\x17write_wells_per_channel\x12/.ont.rpc.production.WriteWellsPerChannelRequest\x1a\x30.ont.rpc.production.WriteWellsPerChannelResponse\"\x00\x12q\n\x12write_product_code\x12+.ont.rpc.production.WriteProductCodeRequest\x1a,.ont.rpc.production.WriteProductCodeResponse\"\x00\x12\x83\x01\n\x18write_temperature_offset\x12\x31.ont.rpc.production.WriteTemperatureOffsetRequest\x1a\x32.ont.rpc.production.WriteTemperatureOffsetResponse\"\x00\x62\x06proto3')
)




_WRITEFLOWCELLDATAREQUEST_EMPTY = _descriptor.Descriptor(
  name='Empty',
  full_name='ont.rpc.production.WriteFlowcellDataRequest.Empty',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=426,
  serialized_end=433,
)

_WRITEFLOWCELLDATAREQUEST_VERSION1 = _descriptor.Descriptor(
  name='Version1',
  full_name='ont.rpc.production.WriteFlowcellDataRequest.Version1',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='flowcell_id', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version1.flowcell_id', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=435,
  serialized_end=466,
)

_WRITEFLOWCELLDATAREQUEST_VERSION2 = _descriptor.Descriptor(
  name='Version2',
  full_name='ont.rpc.production.WriteFlowcellDataRequest.Version2',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='wells_per_channel', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version2.wells_per_channel', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='flowcell_id', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version2.flowcell_id', index=1,
      number=2, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=468,
  serialized_end=526,
)

_WRITEFLOWCELLDATAREQUEST_VERSION3 = _descriptor.Descriptor(
  name='Version3',
  full_name='ont.rpc.production.WriteFlowcellDataRequest.Version3',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='minor_version', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version3.minor_version', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='wells_per_channel', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version3.wells_per_channel', index=1,
      number=2, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='temperature_offset', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version3.temperature_offset', index=2,
      number=3, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='flowcell_id', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version3.flowcell_id', index=3,
      number=4, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='product_code', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version3.product_code', index=4,
      number=5, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='temperature_offset_nullable', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version3.temperature_offset_nullable',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=529,
  serialized_end=693,
)

_WRITEFLOWCELLDATAREQUEST_VERSION4 = _descriptor.Descriptor(
  name='Version4',
  full_name='ont.rpc.production.WriteFlowcellDataRequest.Version4',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='minor_version', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version4.minor_version', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='temperature_offset', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version4.temperature_offset', index=1,
      number=2, type=17, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='adapter_id', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version4.adapter_id', index=2,
      number=3, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='temperature_offset_nullable', full_name='ont.rpc.production.WriteFlowcellDataRequest.Version4.temperature_offset_nullable',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=695,
  serialized_end=809,
)

_WRITEFLOWCELLDATAREQUEST = _descriptor.Descriptor(
  name='WriteFlowcellDataRequest',
  full_name='ont.rpc.production.WriteFlowcellDataRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='empty', full_name='ont.rpc.production.WriteFlowcellDataRequest.empty', index=0,
      number=1, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='v1', full_name='ont.rpc.production.WriteFlowcellDataRequest.v1', index=1,
      number=2, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='v2', full_name='ont.rpc.production.WriteFlowcellDataRequest.v2', index=2,
      number=3, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='v3', full_name='ont.rpc.production.WriteFlowcellDataRequest.v3', index=3,
      number=4, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
    _descriptor.FieldDescriptor(
      name='v4', full_name='ont.rpc.production.WriteFlowcellDataRequest.v4', index=4,
      number=5, type=11, cpp_type=10, label=1,
      has_default_value=False, default_value=None,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[_WRITEFLOWCELLDATAREQUEST_EMPTY, _WRITEFLOWCELLDATAREQUEST_VERSION1, _WRITEFLOWCELLDATAREQUEST_VERSION2, _WRITEFLOWCELLDATAREQUEST_VERSION3, _WRITEFLOWCELLDATAREQUEST_VERSION4, ],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='data', full_name='ont.rpc.production.WriteFlowcellDataRequest.data',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=53,
  serialized_end=817,
)


_WRITEFLOWCELLDATARESPONSE = _descriptor.Descriptor(
  name='WriteFlowcellDataResponse',
  full_name='ont.rpc.production.WriteFlowcellDataResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=819,
  serialized_end=846,
)


_WRITEFLOWCELLIDREQUEST = _descriptor.Descriptor(
  name='WriteFlowcellIdRequest',
  full_name='ont.rpc.production.WriteFlowcellIdRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='flowcell_id', full_name='ont.rpc.production.WriteFlowcellIdRequest.flowcell_id', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=848,
  serialized_end=893,
)


_WRITEFLOWCELLIDRESPONSE = _descriptor.Descriptor(
  name='WriteFlowcellIdResponse',
  full_name='ont.rpc.production.WriteFlowcellIdResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=895,
  serialized_end=920,
)


_WRITEWELLSPERCHANNELREQUEST = _descriptor.Descriptor(
  name='WriteWellsPerChannelRequest',
  full_name='ont.rpc.production.WriteWellsPerChannelRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='wells_per_channel', full_name='ont.rpc.production.WriteWellsPerChannelRequest.wells_per_channel', index=0,
      number=1, type=13, cpp_type=3, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=922,
  serialized_end=978,
)


_WRITEWELLSPERCHANNELRESPONSE = _descriptor.Descriptor(
  name='WriteWellsPerChannelResponse',
  full_name='ont.rpc.production.WriteWellsPerChannelResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=980,
  serialized_end=1010,
)


_WRITEPRODUCTCODEREQUEST = _descriptor.Descriptor(
  name='WriteProductCodeRequest',
  full_name='ont.rpc.production.WriteProductCodeRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='product_code', full_name='ont.rpc.production.WriteProductCodeRequest.product_code', index=0,
      number=1, type=9, cpp_type=9, label=1,
      has_default_value=False, default_value=_b("").decode('utf-8'),
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1012,
  serialized_end=1059,
)


_WRITEPRODUCTCODERESPONSE = _descriptor.Descriptor(
  name='WriteProductCodeResponse',
  full_name='ont.rpc.production.WriteProductCodeResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1061,
  serialized_end=1087,
)


_WRITETEMPERATUREOFFSETREQUEST = _descriptor.Descriptor(
  name='WriteTemperatureOffsetRequest',
  full_name='ont.rpc.production.WriteTemperatureOffsetRequest',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
    _descriptor.FieldDescriptor(
      name='offset', full_name='ont.rpc.production.WriteTemperatureOffsetRequest.offset', index=0,
      number=1, type=5, cpp_type=1, label=1,
      has_default_value=False, default_value=0,
      message_type=None, enum_type=None, containing_type=None,
      is_extension=False, extension_scope=None,
      options=None, file=DESCRIPTOR),
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
    _descriptor.OneofDescriptor(
      name='offset_nullable', full_name='ont.rpc.production.WriteTemperatureOffsetRequest.offset_nullable',
      index=0, containing_type=None, fields=[]),
  ],
  serialized_start=1089,
  serialized_end=1157,
)


_WRITETEMPERATUREOFFSETRESPONSE = _descriptor.Descriptor(
  name='WriteTemperatureOffsetResponse',
  full_name='ont.rpc.production.WriteTemperatureOffsetResponse',
  filename=None,
  file=DESCRIPTOR,
  containing_type=None,
  fields=[
  ],
  extensions=[
  ],
  nested_types=[],
  enum_types=[
  ],
  options=None,
  is_extendable=False,
  syntax='proto3',
  extension_ranges=[],
  oneofs=[
  ],
  serialized_start=1159,
  serialized_end=1191,
)

_WRITEFLOWCELLDATAREQUEST_EMPTY.containing_type = _WRITEFLOWCELLDATAREQUEST
_WRITEFLOWCELLDATAREQUEST_VERSION1.containing_type = _WRITEFLOWCELLDATAREQUEST
_WRITEFLOWCELLDATAREQUEST_VERSION2.containing_type = _WRITEFLOWCELLDATAREQUEST
_WRITEFLOWCELLDATAREQUEST_VERSION3.containing_type = _WRITEFLOWCELLDATAREQUEST
_WRITEFLOWCELLDATAREQUEST_VERSION3.oneofs_by_name['temperature_offset_nullable'].fields.append(
  _WRITEFLOWCELLDATAREQUEST_VERSION3.fields_by_name['temperature_offset'])
_WRITEFLOWCELLDATAREQUEST_VERSION3.fields_by_name['temperature_offset'].containing_oneof = _WRITEFLOWCELLDATAREQUEST_VERSION3.oneofs_by_name['temperature_offset_nullable']
_WRITEFLOWCELLDATAREQUEST_VERSION4.containing_type = _WRITEFLOWCELLDATAREQUEST
_WRITEFLOWCELLDATAREQUEST_VERSION4.oneofs_by_name['temperature_offset_nullable'].fields.append(
  _WRITEFLOWCELLDATAREQUEST_VERSION4.fields_by_name['temperature_offset'])
_WRITEFLOWCELLDATAREQUEST_VERSION4.fields_by_name['temperature_offset'].containing_oneof = _WRITEFLOWCELLDATAREQUEST_VERSION4.oneofs_by_name['temperature_offset_nullable']
_WRITEFLOWCELLDATAREQUEST.fields_by_name['empty'].message_type = _WRITEFLOWCELLDATAREQUEST_EMPTY
_WRITEFLOWCELLDATAREQUEST.fields_by_name['v1'].message_type = _WRITEFLOWCELLDATAREQUEST_VERSION1
_WRITEFLOWCELLDATAREQUEST.fields_by_name['v2'].message_type = _WRITEFLOWCELLDATAREQUEST_VERSION2
_WRITEFLOWCELLDATAREQUEST.fields_by_name['v3'].message_type = _WRITEFLOWCELLDATAREQUEST_VERSION3
_WRITEFLOWCELLDATAREQUEST.fields_by_name['v4'].message_type = _WRITEFLOWCELLDATAREQUEST_VERSION4
_WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data'].fields.append(
  _WRITEFLOWCELLDATAREQUEST.fields_by_name['empty'])
_WRITEFLOWCELLDATAREQUEST.fields_by_name['empty'].containing_oneof = _WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data']
_WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data'].fields.append(
  _WRITEFLOWCELLDATAREQUEST.fields_by_name['v1'])
_WRITEFLOWCELLDATAREQUEST.fields_by_name['v1'].containing_oneof = _WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data']
_WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data'].fields.append(
  _WRITEFLOWCELLDATAREQUEST.fields_by_name['v2'])
_WRITEFLOWCELLDATAREQUEST.fields_by_name['v2'].containing_oneof = _WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data']
_WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data'].fields.append(
  _WRITEFLOWCELLDATAREQUEST.fields_by_name['v3'])
_WRITEFLOWCELLDATAREQUEST.fields_by_name['v3'].containing_oneof = _WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data']
_WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data'].fields.append(
  _WRITEFLOWCELLDATAREQUEST.fields_by_name['v4'])
_WRITEFLOWCELLDATAREQUEST.fields_by_name['v4'].containing_oneof = _WRITEFLOWCELLDATAREQUEST.oneofs_by_name['data']
_WRITETEMPERATUREOFFSETREQUEST.oneofs_by_name['offset_nullable'].fields.append(
  _WRITETEMPERATUREOFFSETREQUEST.fields_by_name['offset'])
_WRITETEMPERATUREOFFSETREQUEST.fields_by_name['offset'].containing_oneof = _WRITETEMPERATUREOFFSETREQUEST.oneofs_by_name['offset_nullable']
DESCRIPTOR.message_types_by_name['WriteFlowcellDataRequest'] = _WRITEFLOWCELLDATAREQUEST
DESCRIPTOR.message_types_by_name['WriteFlowcellDataResponse'] = _WRITEFLOWCELLDATARESPONSE
DESCRIPTOR.message_types_by_name['WriteFlowcellIdRequest'] = _WRITEFLOWCELLIDREQUEST
DESCRIPTOR.message_types_by_name['WriteFlowcellIdResponse'] = _WRITEFLOWCELLIDRESPONSE
DESCRIPTOR.message_types_by_name['WriteWellsPerChannelRequest'] = _WRITEWELLSPERCHANNELREQUEST
DESCRIPTOR.message_types_by_name['WriteWellsPerChannelResponse'] = _WRITEWELLSPERCHANNELRESPONSE
DESCRIPTOR.message_types_by_name['WriteProductCodeRequest'] = _WRITEPRODUCTCODEREQUEST
DESCRIPTOR.message_types_by_name['WriteProductCodeResponse'] = _WRITEPRODUCTCODERESPONSE
DESCRIPTOR.message_types_by_name['WriteTemperatureOffsetRequest'] = _WRITETEMPERATUREOFFSETREQUEST
DESCRIPTOR.message_types_by_name['WriteTemperatureOffsetResponse'] = _WRITETEMPERATUREOFFSETRESPONSE
_sym_db.RegisterFileDescriptor(DESCRIPTOR)

WriteFlowcellDataRequest = _reflection.GeneratedProtocolMessageType('WriteFlowcellDataRequest', (_message.Message,), dict(

  Empty = _reflection.GeneratedProtocolMessageType('Empty', (_message.Message,), dict(
    DESCRIPTOR = _WRITEFLOWCELLDATAREQUEST_EMPTY,
    __module__ = 'minFQ.rpc.production_pb2'
    # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellDataRequest.Empty)
    ))
  ,

  Version1 = _reflection.GeneratedProtocolMessageType('Version1', (_message.Message,), dict(
    DESCRIPTOR = _WRITEFLOWCELLDATAREQUEST_VERSION1,
    __module__ = 'minFQ.rpc.production_pb2'
    # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellDataRequest.Version1)
    ))
  ,

  Version2 = _reflection.GeneratedProtocolMessageType('Version2', (_message.Message,), dict(
    DESCRIPTOR = _WRITEFLOWCELLDATAREQUEST_VERSION2,
    __module__ = 'minFQ.rpc.production_pb2'
    # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellDataRequest.Version2)
    ))
  ,

  Version3 = _reflection.GeneratedProtocolMessageType('Version3', (_message.Message,), dict(
    DESCRIPTOR = _WRITEFLOWCELLDATAREQUEST_VERSION3,
    __module__ = 'minFQ.rpc.production_pb2'
    # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellDataRequest.Version3)
    ))
  ,

  Version4 = _reflection.GeneratedProtocolMessageType('Version4', (_message.Message,), dict(
    DESCRIPTOR = _WRITEFLOWCELLDATAREQUEST_VERSION4,
    __module__ = 'minFQ.rpc.production_pb2'
    # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellDataRequest.Version4)
    ))
  ,
  DESCRIPTOR = _WRITEFLOWCELLDATAREQUEST,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellDataRequest)
  ))
_sym_db.RegisterMessage(WriteFlowcellDataRequest)
_sym_db.RegisterMessage(WriteFlowcellDataRequest.Empty)
_sym_db.RegisterMessage(WriteFlowcellDataRequest.Version1)
_sym_db.RegisterMessage(WriteFlowcellDataRequest.Version2)
_sym_db.RegisterMessage(WriteFlowcellDataRequest.Version3)
_sym_db.RegisterMessage(WriteFlowcellDataRequest.Version4)

WriteFlowcellDataResponse = _reflection.GeneratedProtocolMessageType('WriteFlowcellDataResponse', (_message.Message,), dict(
  DESCRIPTOR = _WRITEFLOWCELLDATARESPONSE,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellDataResponse)
  ))
_sym_db.RegisterMessage(WriteFlowcellDataResponse)

WriteFlowcellIdRequest = _reflection.GeneratedProtocolMessageType('WriteFlowcellIdRequest', (_message.Message,), dict(
  DESCRIPTOR = _WRITEFLOWCELLIDREQUEST,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellIdRequest)
  ))
_sym_db.RegisterMessage(WriteFlowcellIdRequest)

WriteFlowcellIdResponse = _reflection.GeneratedProtocolMessageType('WriteFlowcellIdResponse', (_message.Message,), dict(
  DESCRIPTOR = _WRITEFLOWCELLIDRESPONSE,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteFlowcellIdResponse)
  ))
_sym_db.RegisterMessage(WriteFlowcellIdResponse)

WriteWellsPerChannelRequest = _reflection.GeneratedProtocolMessageType('WriteWellsPerChannelRequest', (_message.Message,), dict(
  DESCRIPTOR = _WRITEWELLSPERCHANNELREQUEST,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteWellsPerChannelRequest)
  ))
_sym_db.RegisterMessage(WriteWellsPerChannelRequest)

WriteWellsPerChannelResponse = _reflection.GeneratedProtocolMessageType('WriteWellsPerChannelResponse', (_message.Message,), dict(
  DESCRIPTOR = _WRITEWELLSPERCHANNELRESPONSE,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteWellsPerChannelResponse)
  ))
_sym_db.RegisterMessage(WriteWellsPerChannelResponse)

WriteProductCodeRequest = _reflection.GeneratedProtocolMessageType('WriteProductCodeRequest', (_message.Message,), dict(
  DESCRIPTOR = _WRITEPRODUCTCODEREQUEST,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteProductCodeRequest)
  ))
_sym_db.RegisterMessage(WriteProductCodeRequest)

WriteProductCodeResponse = _reflection.GeneratedProtocolMessageType('WriteProductCodeResponse', (_message.Message,), dict(
  DESCRIPTOR = _WRITEPRODUCTCODERESPONSE,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteProductCodeResponse)
  ))
_sym_db.RegisterMessage(WriteProductCodeResponse)

WriteTemperatureOffsetRequest = _reflection.GeneratedProtocolMessageType('WriteTemperatureOffsetRequest', (_message.Message,), dict(
  DESCRIPTOR = _WRITETEMPERATUREOFFSETREQUEST,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteTemperatureOffsetRequest)
  ))
_sym_db.RegisterMessage(WriteTemperatureOffsetRequest)

WriteTemperatureOffsetResponse = _reflection.GeneratedProtocolMessageType('WriteTemperatureOffsetResponse', (_message.Message,), dict(
  DESCRIPTOR = _WRITETEMPERATUREOFFSETRESPONSE,
  __module__ = 'minFQ.rpc.production_pb2'
  # @@protoc_insertion_point(class_scope:ont.rpc.production.WriteTemperatureOffsetResponse)
  ))
_sym_db.RegisterMessage(WriteTemperatureOffsetResponse)



_PRODUCTIONSERVICE = _descriptor.ServiceDescriptor(
  name='ProductionService',
  full_name='ont.rpc.production.ProductionService',
  file=DESCRIPTOR,
  index=0,
  options=None,
  serialized_start=1194,
  serialized_end=1820,
  methods=[
  _descriptor.MethodDescriptor(
    name='write_flowcell_data',
    full_name='ont.rpc.production.ProductionService.write_flowcell_data',
    index=0,
    containing_service=None,
    input_type=_WRITEFLOWCELLDATAREQUEST,
    output_type=_WRITEFLOWCELLDATARESPONSE,
    options=None,
  ),
  _descriptor.MethodDescriptor(
    name='write_flowcell_id',
    full_name='ont.rpc.production.ProductionService.write_flowcell_id',
    index=1,
    containing_service=None,
    input_type=_WRITEFLOWCELLIDREQUEST,
    output_type=_WRITEFLOWCELLIDRESPONSE,
    options=None,
  ),
  _descriptor.MethodDescriptor(
    name='write_wells_per_channel',
    full_name='ont.rpc.production.ProductionService.write_wells_per_channel',
    index=2,
    containing_service=None,
    input_type=_WRITEWELLSPERCHANNELREQUEST,
    output_type=_WRITEWELLSPERCHANNELRESPONSE,
    options=None,
  ),
  _descriptor.MethodDescriptor(
    name='write_product_code',
    full_name='ont.rpc.production.ProductionService.write_product_code',
    index=3,
    containing_service=None,
    input_type=_WRITEPRODUCTCODEREQUEST,
    output_type=_WRITEPRODUCTCODERESPONSE,
    options=None,
  ),
  _descriptor.MethodDescriptor(
    name='write_temperature_offset',
    full_name='ont.rpc.production.ProductionService.write_temperature_offset',
    index=4,
    containing_service=None,
    input_type=_WRITETEMPERATUREOFFSETREQUEST,
    output_type=_WRITETEMPERATUREOFFSETRESPONSE,
    options=None,
  ),
])
_sym_db.RegisterServiceDescriptor(_PRODUCTIONSERVICE)

DESCRIPTOR.services_by_name['ProductionService'] = _PRODUCTIONSERVICE

# @@protoc_insertion_point(module_scope)
