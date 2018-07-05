### THIS FILE IS AUTOGENERATED. DO NOT EDIT THIS FILE DIRECTLY ###
from .device_pb2_grpc import *
from . import device_pb2
from minFQ.rpc.device_pb2 import *
from minFQ.rpc._support import MessageWrapper, ArgumentError

__all__ = [
    "DeviceService",
    "ChannelConfiguration",
    "GetDeviceInfoRequest",
    "GetDeviceInfoResponse",
    "GetDeviceStateRequest",
    "GetDeviceStateResponse",
    "StreamDeviceStateRequest",
    "GetFlowCellInfoRequest",
    "GetFlowCellInfoResponse",
    "StreamFlowCellInfoRequest",
    "SetUserSpecifiedFlowCellIdRequest",
    "SetUserSpecifiedFlowCellIdResponse",
    "SetUserSpecifiedProductCodeRequest",
    "SetUserSpecifiedProductCodeResponse",
    "SetCalibrationRequest",
    "SetCalibrationResponse",
    "ClearCalibrationRequest",
    "ClearCalibrationResponse",
    "ResetDeviceSettingsRequest",
    "ResetDeviceSettingsResponse",
    "GetCalibrationRequest",
    "GetCalibrationResponse",
    "SetTemperatureRequest",
    "SetTemperatureResponse",
    "GetTemperatureRequest",
    "GetTemperatureResponse",
    "UnblockRequest",
    "UnblockResponse",
    "GetChannelConfigurationRequest",
    "GetChannelConfigurationResponse",
    "SetChannelConfigurationRequest",
    "SetChannelConfigurationResponse",
    "SetChannelConfigurationAllRequest",
    "SetChannelConfigurationAllResponse",
    "SaturationConfig",
    "SetSaturationConfigRequest",
    "SetSaturationConfigResponse",
    "GetSaturationConfigRequest",
    "GetSaturationConfigResponse",
    "GetSampleRateRequest",
    "GetSampleRateResponse",
    "SetSampleRateRequest",
    "SetSampleRateResponse",
    "GetBiasVoltageRequest",
    "GetBiasVoltageResponse",
    "SetBiasVoltageRequest",
    "SetBiasVoltageResponse",
    "GetChannelsLayoutRequest",
    "GetChannelsLayoutResponse",
    "ChannelRecord",
    "SelectedWell",
    "WELL_NONE",
    "WELL_1",
    "WELL_2",
    "WELL_3",
    "WELL_4",
    "WELL_OTHER",
]

class DeviceService(object):
    def __init__(self, channel):
        self._stub = DeviceServiceStub(channel)
        self._pb = device_pb2

    def get_device_info(self, _message=None, _timeout=None, **kwargs):
        """
        Get information about the device this MinKNOW instance was started for.

        In normal circumstances (ie: when using the manager service), a new MinKNOW instance
        is started for each available device. This call provides information about this device.

        The information returned by this call will not change (providing the MinKNOW instance
        was started by the manager service).

        :rtype: GetDeviceInfoResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_device_info(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetDeviceInfoRequest()

        if len(unused_args) > 0:
            raise ArgumentError("get_device_info got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_device_info(_message, timeout=_timeout), unwraps=[])

    def get_device_state(self, _message=None, _timeout=None, **kwargs):
        """
        Get information about the current device state.

        Information in this call may change as the device is used with MinKNOW, for example,
        by unplugging or plugging in the device.
        Since 1.12

        :rtype: GetDeviceStateResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_device_state(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetDeviceStateRequest()

        if len(unused_args) > 0:
            raise ArgumentError("get_device_state got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_device_state(_message, timeout=_timeout), unwraps=[])

    def stream_device_state(self, _message=None, _timeout=None, **kwargs):
        """
        Streaming version of get_device_state

        Since 1.13

        :rtype: GetDeviceStateResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.stream_device_state(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = StreamDeviceStateRequest()

        if len(unused_args) > 0:
            raise ArgumentError("stream_device_state got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.stream_device_state(_message, timeout=_timeout), unwraps=[])

    def reset_device_settings(self, _message=None, _timeout=None, **kwargs):
        """
        Reset all settings associate with the current device.

        This call will initialise all settings to their default state, ie the same as when MinKNOW boots.

        :rtype: ResetDeviceSettingsResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.reset_device_settings(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = ResetDeviceSettingsRequest()

        if len(unused_args) > 0:
            raise ArgumentError("reset_device_settings got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.reset_device_settings(_message, timeout=_timeout), unwraps=[])

    def get_flow_cell_info(self, _message=None, _timeout=None, **kwargs):
        """
        Get information about the flow cell (if any).

        This provides information about the flow_cell attached to the device (described by
        get_device_info()), if any.

        :rtype: GetFlowCellInfoResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_flow_cell_info(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetFlowCellInfoRequest()

        if len(unused_args) > 0:
            raise ArgumentError("get_flow_cell_info got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_flow_cell_info(_message, timeout=_timeout), unwraps=[])

    def stream_flow_cell_info(self, _message=None, _timeout=None, **kwargs):
        """
        Streaming version of get_flow_cell_info

        Since 1.13

        :rtype: GetFlowCellInfoResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.stream_flow_cell_info(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = StreamFlowCellInfoRequest()

        if len(unused_args) > 0:
            raise ArgumentError("stream_flow_cell_info got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.stream_flow_cell_info(_message, timeout=_timeout), unwraps=[])

    def set_user_specified_flow_cell_id(self, _message=None, _timeout=None, **kwargs):
        """
        Set the user specified flow cell id.

        This changes the user specified flow cell id.
        MinKNOW will use this id in place of the id read from the eeprom, if no eeprom data
        is available.

        This data is reset when the flow cell is disconnected.

        Since 1.12

        :param id: (required)
            A unique identifier for the flow cell, which the user can specify.

            In the event a flow cell does not have an eeprom, this field can be used by the user
            to record their flow_cell_id.

            Since 1.12
        :rtype: SetUserSpecifiedFlowCellIdResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_user_specified_flow_cell_id(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetUserSpecifiedFlowCellIdRequest()

        if 'id' in kwargs:
            unused_args.remove('id')
            _message.id = kwargs['id']
        else:
            raise ArgumentError("set_user_specified_flow_cell_id requires a 'id' argument")

        if len(unused_args) > 0:
            raise ArgumentError("set_user_specified_flow_cell_id got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_user_specified_flow_cell_id(_message, timeout=_timeout), unwraps=[])

    def set_user_specified_product_code(self, _message=None, _timeout=None, **kwargs):
        """
        Set the user specified product code.

        This changes the user specified product code.

        MinKNOW does not use the product code, it is intended for use in MinKNOW's clients.

        This data is reset when the flow cell is disconnected.

        Since 1.12

        :param code: (required)
            A product code for the flow cell, which the user can specify.

            In the event a flow cell does not have an eeprom, the user can specify product code here.

            Since 1.12
        :rtype: SetUserSpecifiedProductCodeResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_user_specified_product_code(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetUserSpecifiedProductCodeRequest()

        if 'code' in kwargs:
            unused_args.remove('code')
            _message.code = kwargs['code']
        else:
            raise ArgumentError("set_user_specified_product_code requires a 'code' argument")

        if len(unused_args) > 0:
            raise ArgumentError("set_user_specified_product_code got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_user_specified_product_code(_message, timeout=_timeout), unwraps=[])

    def set_calibration(self, _message=None, _timeout=None, **kwargs):
        """
        Set the calibration measurements to be used by MinKNOW.

        Calibration describes how to convert from the raw ADC (analog-to-digital converter) values
        from the device into picoamps (pA).

        Note that calibration depends on the device, flow cell and some of the device settings
        (including sampling frequency and the capacitance used in the integratation circuit). If
        any of these are changed, the calibration will no longer be used. Instead, a previously-saved
        calibration (for that combination of flow cell and settings) might be used, or the identity
        calibration might be used.

        On a MinION, the settings that a calibration depends on are sampling frequency and
        integration capacitor.

        :param first_channel: (required)
            The first channel included in calibration data.

            This must always be 1. This is required in order to make sure the client and MinKNOW agree on
            what data is being provided.
        :param last_channel: (required)
            The last channel included in calibration data.

            This must always be the same as the channel count returned by
            :meth:`get_flow_cell_info`. This is required in order to make
            sure the client and MinKNOW agree on what data is being provided.
        :param offsets: (required)
            The ADC value adjustment to reach 0pA on each channel.

            This is ``-x``, where ``x`` is the (mean) ADC value at 0pA.
        :param pa_ranges: (required)
            The range of possible pA values that can be produced by the device.
        :rtype: SetCalibrationResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_calibration(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetCalibrationRequest()

        if 'first_channel' in kwargs:
            unused_args.remove('first_channel')
            _message.first_channel = kwargs['first_channel']
        else:
            raise ArgumentError("set_calibration requires a 'first_channel' argument")

        if 'last_channel' in kwargs:
            unused_args.remove('last_channel')
            _message.last_channel = kwargs['last_channel']
        else:
            raise ArgumentError("set_calibration requires a 'last_channel' argument")

        if 'offsets' in kwargs:
            unused_args.remove('offsets')
            _message.offsets.extend(kwargs['offsets'])
        else:
            raise ArgumentError("set_calibration requires a 'offsets' argument")

        if 'pa_ranges' in kwargs:
            unused_args.remove('pa_ranges')
            _message.pa_ranges.extend(kwargs['pa_ranges'])
        else:
            raise ArgumentError("set_calibration requires a 'pa_ranges' argument")

        if len(unused_args) > 0:
            raise ArgumentError("set_calibration got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_calibration(_message, timeout=_timeout), unwraps=[])

    def clear_calibration(self, _message=None, _timeout=None, **kwargs):
        """
        Clear the current calibration.

        This is the same as setting the calibration to be the identity function (setting all offsets
        to 0, and all pA ranges to the digitisation value).

        :rtype: ClearCalibrationResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.clear_calibration(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = ClearCalibrationRequest()

        if len(unused_args) > 0:
            raise ArgumentError("clear_calibration got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.clear_calibration(_message, timeout=_timeout), unwraps=[])

    def get_calibration(self, _message=None, _timeout=None, **kwargs):
        """
        The calibration measurements being used by MinKNOW.

        Calibration describes how to convert from the raw ADC (analog-to-digital converter) values
        from the device into picoamps (pA).

        To get a pA value from an ADC value the following function is applied::

             pA_current = (adc_current + offset) / (digitisation / pA_range)

        The digitisation is the range of possible ADC values. It is the same for all channels.

        If there is no calibration (including if it was cleared with ``clear_calibration()`` or
        invalidated because of device settings changes), this will return the identity calibration:
        all offsets will be 0, and the pA ranges will be the same as the digitisation.

        :param first_channel: (required)
            The first channel to get calibration data for.

            This should normally be 1.
        :param last_channel: (required)
            The last channel included in calibration data.

            This should normally be the channel count returned by
            :meth:`get_flow_cell_info`.
        :rtype: GetCalibrationResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_calibration(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetCalibrationRequest()

        if 'first_channel' in kwargs:
            unused_args.remove('first_channel')
            _message.first_channel = kwargs['first_channel']
        else:
            raise ArgumentError("get_calibration requires a 'first_channel' argument")

        if 'last_channel' in kwargs:
            unused_args.remove('last_channel')
            _message.last_channel = kwargs['last_channel']
        else:
            raise ArgumentError("get_calibration requires a 'last_channel' argument")

        if len(unused_args) > 0:
            raise ArgumentError("get_calibration got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_calibration(_message, timeout=_timeout), unwraps=[])

    def set_temperature(self, _message=None, _timeout=None, **kwargs):
        """
        If the device is capable (see GetDeviceInfoResponse.temperature_controllable)
        then this sets the minimum and maximum temperatures of the flow-cell.

        :param temperature:
            The desired temperature in degrees Celsius.

            If temperature control is supported and enabled, the device will attempt to keep its
            temperature at this value. See the ``can_set_temperature`` field returned by the
            DeviceService.get_device_info() RPC.
        :param wait_for_temperature:
            Settings which can be specified in order to wait for the temperature to be reached.

            Since 1.15
        :rtype: SetTemperatureResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_temperature(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetTemperatureRequest()

        if 'temperature' in kwargs:
            unused_args.remove('temperature')
            _message.temperature = kwargs['temperature']

        if 'wait_for_temperature' in kwargs:
            unused_args.remove('wait_for_temperature')
            _message.wait_for_temperature.CopyFrom(kwargs['wait_for_temperature'])

        if len(unused_args) > 0:
            raise ArgumentError("set_temperature got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_temperature(_message, timeout=_timeout), unwraps=[])

    def get_temperature(self, _message=None, _timeout=None, **kwargs):
        """
        Get the current temperature of the device.

        Since 1.11

        :rtype: GetTemperatureResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_temperature(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetTemperatureRequest()

        if len(unused_args) > 0:
            raise ArgumentError("get_temperature got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_temperature(_message, timeout=_timeout), unwraps=[])

    def unblock(self, _message=None, _timeout=None, **kwargs):
        """
        Triggers an unblock for a list of channels for a given duration (Please see UnblockRequest).
        It will start an unblock for every channel received as a parameter, then this RPC returns.
        After the timeout expires (the duration in seconds given in the request), the return from
        unblock is automatically triggered, which resets the channel configuration (mux) to the
        value preceding the unblock. 

        Notes!!

        During the unblock the user should NOT do any mux changes, as the unblock will be interrupted.
        On Promethion this would be even more complicated, as an unblock would normally restore
        hardware saturation. If an unblock is interrupted it will not restore the state to the original
        one.

        The user should NOT change the overload mode during an unblock - this will confuse the return from
        unblock, which tries to reset the overload mode to the state preceeding the unblock.

        The unblock can fail if the channel is not in a valid well state (this means a channel needs to be
        in one of pore1-4, not test current, regen pore or unblock). If a mux is not valid, the unblock grpc
        will try to continue for the rest of the channels, ignoring the one with the wrong mux.

        :param channels:
            / List of channels indexed from 1.
        :param duration_in_seconds:
        :param duration_in_milliseconds:
        :rtype: UnblockResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.unblock(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        # check oneof group 'duration'
        oneof_fields = set([
            'duration_in_seconds',
            'duration_in_milliseconds',
        ])
        if len(unused_args & oneof_fields) > 1:
            raise ArgumentError("unblock given multiple conflicting arguments: '{}'".format("', '".join(unused_args & oneof_fields)))
        _message = UnblockRequest()

        if 'channels' in kwargs:
            unused_args.remove('channels')
            _message.channels.extend(kwargs['channels'])

        if 'duration_in_seconds' in kwargs:
            unused_args.remove('duration_in_seconds')
            _message.duration_in_seconds = kwargs['duration_in_seconds']

        if 'duration_in_milliseconds' in kwargs:
            unused_args.remove('duration_in_milliseconds')
            _message.duration_in_milliseconds = kwargs['duration_in_milliseconds']

        if len(unused_args) > 0:
            raise ArgumentError("unblock got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.unblock(_message, timeout=_timeout), unwraps=[])

    def get_channel_configuration(self, _message=None, _timeout=None, **kwargs):
        """
        Get the channel configuration for any number of channels

        The maximum addressable channel will depend on the device. Currently this will be 512 on a MinION/GridION
        and 4096 on a PromethION

        :param channels:
            A list of channel names (1-indexed) to specify what channels to get channel configs for

            Will return an error if any of the channel names are below 1, or above the channel count value
            returned from :meth:`get_flow_cell_info`
        :rtype: GetChannelConfigurationResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_channel_configuration(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetChannelConfigurationRequest()

        if 'channels' in kwargs:
            unused_args.remove('channels')
            _message.channels.extend(kwargs['channels'])

        if len(unused_args) > 0:
            raise ArgumentError("get_channel_configuration got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_channel_configuration(_message, timeout=_timeout), unwraps=[])

    def set_channel_configuration(self, _message=None, _timeout=None, **kwargs):
        """
        Set the channel configuration for any number of channels

        The maximum addressable channel will depend on the device. Currently this will be 512 on a MinION/GridION
        and 4096 on a PromethION.

        :param channel_configurations:
            A map between <channel name, config to set>

            Will return an error if any of the key values (representing channel names) are below 1, or 
            above the channel count value returned from :meth:`get_flow_cell_info`

            The selected well cannot be set to WELL_OTHER, and will error if it tries to do so
        :rtype: SetChannelConfigurationResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_channel_configuration(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetChannelConfigurationRequest()

        if 'channel_configurations' in kwargs:
            unused_args.remove('channel_configurations')
            for key, value in kwargs['channel_configurations'].items():
                _message.channel_configurations[key].CopyFrom(value)

        if len(unused_args) > 0:
            raise ArgumentError("set_channel_configuration got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_channel_configuration(_message, timeout=_timeout), unwraps=[])

    def set_channel_configuration_all(self, _message=None, _timeout=None, **kwargs):
        """

        :param well:
            The currently-connected well.

            Wells are counted from 1. 0 indicates that no well is connected. 5 indicates some non-generic configuration
            such as ground for a minion or connecting all wells on promethion

            Note that MinKNOW can return channel configurations where the well number is larger than the
            ``max_well_count`` value returned by :meth:`DeviceService.get_device_info`. This indicates
            that some other connection has been made (for example, PromethIONs can simultaneously
            connect all wells, and MinIONs can connect to ground).
        :param test_current:
            Whether the test current is connected to the integrator (measurement circuit).

            The signal will be a steady test current produced on the device. This can be used for
            calibration or to test the device integration circuits.
        :param regeneration:
            Please DO NOT USE - does not have a practical use, will be removed in later versions.
            Whether the regeneration current is connected to the integrator (measurement circuit).

            This is similar to unblock, but uses a different circuit. It is not available on MinION or
            GridION devices.
        :param unblock:
            Whether the unblock voltage is connected to the integrator (measurement circuit).

            Provides a reverse potential across the connected well. This can be used to drive molecules
            back out of the well.
        :rtype: SetChannelConfigurationAllResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_channel_configuration_all(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetChannelConfigurationAllRequest()

        if 'well' in kwargs:
            unused_args.remove('well')
            _message.channel_configuration.well = kwargs['well']

        if 'test_current' in kwargs:
            unused_args.remove('test_current')
            _message.channel_configuration.test_current = kwargs['test_current']

        if 'regeneration' in kwargs:
            unused_args.remove('regeneration')
            _message.channel_configuration.regeneration = kwargs['regeneration']

        if 'unblock' in kwargs:
            unused_args.remove('unblock')
            _message.channel_configuration.unblock = kwargs['unblock']

        if len(unused_args) > 0:
            raise ArgumentError("set_channel_configuration_all got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_channel_configuration_all(_message, timeout=_timeout), unwraps=[])

    def set_saturation_config(self, _message=None, _timeout=None, **kwargs):
        """
        Set the saturation control configuration.

        The request is immediately sent to the data acquisition module, and applied. All settings can be changed
        whilst the experiment is running.

        If any keys are not specified when this method is called (see the message for specific optional parameters),
        the previously applied parameters are kept; initially, when this method has never been called, defaults from the
        application config are used.

        note: calling this method resets anu in-progress saturations when it is called, causing them to need to start
        saturation counts again, this may mean any saturations may take longer to occur.

        :param thresholds:
            Settings for saturation count thresholds, this controls how long a
            saturated value must be over limit before the channel is turned off.

            If not specified, the previous thresholds are kept.
        :param software_saturation:
            Settings for software saturation, specified in adc units of the device.

            If not specified, the previous thresholds are kept.
        :param user_threshold_saturation:
            Settings for user threshold saturation, specified in pA.

            If not specified, the previous thresholds are kept.
        :rtype: SetSaturationConfigResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_saturation_config(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetSaturationConfigRequest()

        if 'thresholds' in kwargs:
            unused_args.remove('thresholds')
            _message.settings.thresholds.CopyFrom(kwargs['thresholds'])

        if 'software_saturation' in kwargs:
            unused_args.remove('software_saturation')
            _message.settings.software_saturation.CopyFrom(kwargs['software_saturation'])

        if 'user_threshold_saturation' in kwargs:
            unused_args.remove('user_threshold_saturation')
            _message.settings.user_threshold_saturation.CopyFrom(kwargs['user_threshold_saturation'])

        if len(unused_args) > 0:
            raise ArgumentError("set_saturation_config got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_saturation_config(_message, timeout=_timeout), unwraps=[])

    def get_saturation_config(self, _message=None, _timeout=None, **kwargs):
        """
        Get the saturation control configuration.

        The default configuration is specifed by the MinKNOW application configuration, the command returns the most
        recently applied saturation config.

        :rtype: GetSaturationConfigResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_saturation_config(_message, timeout=_timeout), unwraps=["settings"])

        unused_args = set(kwargs.keys())

        _message = GetSaturationConfigRequest()

        if len(unused_args) > 0:
            raise ArgumentError("get_saturation_config got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_saturation_config(_message, timeout=_timeout), unwraps=["settings"])

    def get_sample_rate(self, _message=None, _timeout=None, **kwargs):
        """
        Get the sample rate of the device

        Please refer to MinionDeviceService and PromethionDeviceService for the expected
        return value for a minion and promethion respectively

        :rtype: GetSampleRateResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_sample_rate(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetSampleRateRequest()

        if len(unused_args) > 0:
            raise ArgumentError("get_sample_rate got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_sample_rate(_message, timeout=_timeout), unwraps=[])

    def set_sample_rate(self, _message=None, _timeout=None, **kwargs):
        """
        Set the sample rate of the device, and returns the actual value set on the device

        Please refer to MinionDeviceService and PromethionDeviceService to see
        how the value set here will be used to determine the real sample rate for a
        minion and promethion respectively

        Trying to set the sample rate during an acquisition period will result in an error

        :param sample_rate: (required)
        :rtype: SetSampleRateResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_sample_rate(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetSampleRateRequest()

        if 'sample_rate' in kwargs:
            unused_args.remove('sample_rate')
            _message.sample_rate = kwargs['sample_rate']
        else:
            raise ArgumentError("set_sample_rate requires a 'sample_rate' argument")

        if len(unused_args) > 0:
            raise ArgumentError("set_sample_rate got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_sample_rate(_message, timeout=_timeout), unwraps=[])

    def get_bias_voltage(self, _message=None, _timeout=None, **kwargs):
        """

        :rtype: GetBiasVoltageResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_bias_voltage(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetBiasVoltageRequest()

        if len(unused_args) > 0:
            raise ArgumentError("get_bias_voltage got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_bias_voltage(_message, timeout=_timeout), unwraps=[])

    def set_bias_voltage(self, _message=None, _timeout=None, **kwargs):
        """

        :param bias_voltage: (required)
        :rtype: SetBiasVoltageResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.set_bias_voltage(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = SetBiasVoltageRequest()

        if 'bias_voltage' in kwargs:
            unused_args.remove('bias_voltage')
            _message.bias_voltage = kwargs['bias_voltage']
        else:
            raise ArgumentError("set_bias_voltage requires a 'bias_voltage' argument")

        if len(unused_args) > 0:
            raise ArgumentError("set_bias_voltage got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.set_bias_voltage(_message, timeout=_timeout), unwraps=[])

    def get_channels_layout(self, _message=None, _timeout=None, **kwargs):
        """
        Get information about the channel layout

        Since 1.14

        :rtype: GetChannelsLayoutResponse
        """
        if _message is not None:
            return MessageWrapper(self._stub.get_channels_layout(_message, timeout=_timeout), unwraps=[])

        unused_args = set(kwargs.keys())

        _message = GetChannelsLayoutRequest()

        if len(unused_args) > 0:
            raise ArgumentError("get_channels_layout got unexpected keyword arguments '{}'".format("', '".join(unused_args)))
        return MessageWrapper(self._stub.get_channels_layout(_message, timeout=_timeout), unwraps=[])


