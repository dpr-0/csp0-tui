class APIError(Exception):
    msg = ""


class NetworkError(APIError):
    msg = "network problem"


class ServiceError(APIError):
    msg = "service problem"


class IncorrectPassword(APIError):
    msg = "incorrect password"


class CreateFail(APIError):
    msg = "create fail"


class StillWating(APIError):
    msg = "still waiting"
