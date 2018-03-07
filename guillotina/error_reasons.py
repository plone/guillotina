

class ErrorReason:

    def __init__(self, name, details=''):
        self.name = name
        self.details = details


JSON_DECODE = ErrorReason(
    'jsonDecodeError', 'Failed to parse the JSON payload')
UNKNOWN = ErrorReason('unknownError', 'Encountered unknown error')
UNAUTHORIZED = ErrorReason('unauthorized', 'Not authorized to execute action')
REQUIRED_PARAM_MISSING = ErrorReason(
    'requiredParamMissing', 'Missing required param in the request')
INVALID_ID = ErrorReason('invalidId', 'Invalid ID for object')
PRECONDITION_FAILED = ErrorReason('preconditionFailed', '')
NOT_ALLOWED = ErrorReason('notAllowed', 'Type not allowed to be added here')
CONFLICT_ID = ErrorReason('conflictId', 'This ID already exists')
DESERIALIZATION_FAILED = ErrorReason(
    'deserializationError', 'Could not deserialize the content')
ID_NOT_ALLOWED = ErrorReason('idNotAllowed', '"id" not allowed in payload')
ALREADY_INSTALLED = ErrorReason('alreadyInstalled', 'Addon already installed')
NOT_INSTALLED = ErrorReason('notInstalled', 'Addon not installed')
