class MTConnectionError(Exception):
    """
    Exception raised when we get an unexpected status code from a connection to the minoTour sever
    """

    def __init__(
        self, response, message="Unexpected status code (not in expected values)"
    ):
        """

        Parameters
        ----------
        response: requests.models.Response
            The requests object from the request
        message: str
            The message to display at the bottom of the Exception
        """
        self.response = response
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        """
        Overides the displayed message string
        Returns
        -------
        str
        """
        lookup_message = {401: "Nuh uh - unauthorised", 500: "MinoTour says no"}
        return "{} -> {} -> {} -> {}".format(
            self.response.status_code,
            lookup_message.get(self.response.status_code, ""),
            self.message,
            self.response.text,
        )


def except_rpc(wrapped_function):
    def _wrapper(*args, **kwargs):
        try:
            # do something before the function call
            result = wrapped_function(*args, **kwargs)
            # do something after the function call
        except TypeError:
            print("TypeError")
        except IndexError:
            print("IndexError")
        # return result

    return _wrapper
