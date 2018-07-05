# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from minFQ.rpc import promethion_device_pb2 as minknow_dot_rpc_dot_promethion__device__pb2


class PromethionDeviceServiceStub(object):
  """Interface to control PromethION devices.
  """

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.change_device_settings = channel.unary_unary(
        '/ont.rpc.promethion_device.PromethionDeviceService/change_device_settings',
        request_serializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangeDeviceSettingsRequest.SerializeToString,
        response_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangeDeviceSettingsResponse.FromString,
        )
    self.get_device_settings = channel.unary_unary(
        '/ont.rpc.promethion_device.PromethionDeviceService/get_device_settings',
        request_serializer=minknow_dot_rpc_dot_promethion__device__pb2.GetDeviceSettingsRequest.SerializeToString,
        response_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.GetDeviceSettingsResponse.FromString,
        )
    self.change_pixel_block_settings = channel.unary_unary(
        '/ont.rpc.promethion_device.PromethionDeviceService/change_pixel_block_settings',
        request_serializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangePixelBlockSettingsRequest.SerializeToString,
        response_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangePixelBlockSettingsResponse.FromString,
        )
    self.get_pixel_block_settings = channel.unary_unary(
        '/ont.rpc.promethion_device.PromethionDeviceService/get_pixel_block_settings',
        request_serializer=minknow_dot_rpc_dot_promethion__device__pb2.GetPixelBlockSettingsRequest.SerializeToString,
        response_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.GetPixelBlockSettingsResponse.FromString,
        )
    self.change_pixel_settings = channel.unary_unary(
        '/ont.rpc.promethion_device.PromethionDeviceService/change_pixel_settings',
        request_serializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangePixelSettingsRequest.SerializeToString,
        response_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangePixelSettingsResponse.FromString,
        )
    self.get_pixel_settings = channel.unary_unary(
        '/ont.rpc.promethion_device.PromethionDeviceService/get_pixel_settings',
        request_serializer=minknow_dot_rpc_dot_promethion__device__pb2.GetPixelSettingsRequest.SerializeToString,
        response_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.GetPixelSettingsResponse.FromString,
        )


class PromethionDeviceServiceServicer(object):
  """Interface to control PromethION devices.
  """

  def change_device_settings(self, request, context):
    """Change the settings which apply to the whole device.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def get_device_settings(self, request, context):
    """Get the current settings which apply to the whole device.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def change_pixel_block_settings(self, request, context):
    """Change the settings which apply specific pixel blocks.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def get_pixel_block_settings(self, request, context):
    """Get the settings which apply to specific pixel blocks.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def change_pixel_settings(self, request, context):
    """Change the settings which apply to the referenced pixels.
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def get_pixel_settings(self, request, context):
    """Get the pixel settings for the requested pixel's
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_PromethionDeviceServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'change_device_settings': grpc.unary_unary_rpc_method_handler(
          servicer.change_device_settings,
          request_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangeDeviceSettingsRequest.FromString,
          response_serializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangeDeviceSettingsResponse.SerializeToString,
      ),
      'get_device_settings': grpc.unary_unary_rpc_method_handler(
          servicer.get_device_settings,
          request_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.GetDeviceSettingsRequest.FromString,
          response_serializer=minknow_dot_rpc_dot_promethion__device__pb2.GetDeviceSettingsResponse.SerializeToString,
      ),
      'change_pixel_block_settings': grpc.unary_unary_rpc_method_handler(
          servicer.change_pixel_block_settings,
          request_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangePixelBlockSettingsRequest.FromString,
          response_serializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangePixelBlockSettingsResponse.SerializeToString,
      ),
      'get_pixel_block_settings': grpc.unary_unary_rpc_method_handler(
          servicer.get_pixel_block_settings,
          request_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.GetPixelBlockSettingsRequest.FromString,
          response_serializer=minknow_dot_rpc_dot_promethion__device__pb2.GetPixelBlockSettingsResponse.SerializeToString,
      ),
      'change_pixel_settings': grpc.unary_unary_rpc_method_handler(
          servicer.change_pixel_settings,
          request_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangePixelSettingsRequest.FromString,
          response_serializer=minknow_dot_rpc_dot_promethion__device__pb2.ChangePixelSettingsResponse.SerializeToString,
      ),
      'get_pixel_settings': grpc.unary_unary_rpc_method_handler(
          servicer.get_pixel_settings,
          request_deserializer=minknow_dot_rpc_dot_promethion__device__pb2.GetPixelSettingsRequest.FromString,
          response_serializer=minknow_dot_rpc_dot_promethion__device__pb2.GetPixelSettingsResponse.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'ont.rpc.promethion_device.PromethionDeviceService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
