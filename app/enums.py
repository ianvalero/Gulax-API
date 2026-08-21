from enum import StrEnum

class CollectionDistance(StrEnum):
    COSINE = "Cosine"
    EUCLID = "Euclid"
    DOT = "Dot"

class DocumentVersionStatus(StrEnum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


class IngestionRunStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class TenantSortField(StrEnum):
    ID = "id"
    NAME = "name"
    DESCRIPTION = "description"
    ROLES = "roles"
    CREATED_AT = "created_at"
    CREATED_BY = "created_by"


class KnowledgeSpaceSortField(StrEnum):
    ID = "id"
    TENANT_ID = "tenant_id"
    NAME = "name"
    TENANT_NAME = "tenant_name"
    TENANT_ROLES = "tenant_roles"
    DESCRIPTION = "description"
    CREATED_AT = "created_at"
    CREATED_BY = "created_by"


class DocumentSortField(StrEnum):
    ID = "id"
    KNOWLEDGE_SPACE__ID = "knowledge_space_id"
    KNOWLEDGE_SPACE_NAME = "knowledge_spac_name"
    DESCRIPTION = "description"
    TENANT_ROLES = "tenant_roles"
    CREATED_AT = "created_at"
    CREATED_BY = "created_by"
