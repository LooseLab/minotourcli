import logging

log = logging.getLogger("minknow_connection")


def check_warnings(device_type, minknow_version):
    """
    Check to see if there any compatability warnings for minknow monitorng
    Parameters
    ----------
    device_type: str
        The device name for the sequencer connected to minKNOW. May be one of PROMETHION, GRIDION, MINION
    minknow_version: str
        The version of minknow that we are using.

    Returns
    -------

    """
    if device_type == "PROMETHION":
        log.warning("This version of minFQ may not be compatible with PromethION.")
    if minknow_version.startswith("3.3"):
        log.warning(
            "This version of minFQ may not be compatible with the MinKNOW version you are running."
        )
        log.warning("As a consequence, live monitoring MAY NOT WORK. We recommend using minknow 4.0.X")
        log.warning("If you experience problems, let us know.")