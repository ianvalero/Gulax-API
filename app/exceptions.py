class AppException(Exception):
    status_code = 500

    def __init__(self, detail: str):
        self.detail = detail


class InvalidAutomationTokenError(AppException):
    status_code = 401

class InvalidApiKeyError(AppException):
    status_code = 401

class UserNotFoundError(AppException):
    status_code = 404

class TenantNameConflictError(AppException):
    status_code = 409

class TenantPermissionError(AppException):
    status_code = 403

class TenantNotFoundError(AppException):
    status_code = 404

class DocumentNotFoundError(AppException):
    status_code = 404

class KnowledgeSpaceNameConflictError(AppException):
    status_code = 409

class KnowledgeSpaceNotFoundError(AppException):
    status_code = 404

class KnowledgeSpacePermissionError(AppException):
    status_code = 403

class DocumentVersionNotFoundError(AppException):
    status_code = 404

class DocumentVersionConflictError(AppException):
    status_code = 409

class FileValidationError(AppException):
    status_code = 400

class IngestionRunNotFoundError(AppException):
    status_code = 404

class CeleryTaskNotFoundError(AppException):
    status_code = 404

class CeleryTaskEnqueueError(AppException):
    status_code = 503

class QdrantOperationError(AppException):
    status_code = 503

class EmbeddingServiceError(AppException):
    status_code = 503
