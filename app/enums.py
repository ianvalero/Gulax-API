from enum import StrEnum

class CollectionDistance(StrEnum):
    COSINE = "Cosine"
    EUCLID = "Euclid"
    DOT = "Dot"

class DocumentVersionStatus(StrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    ACTIVE = "ACTIVE"
    FAILED = "FAILED"
    ARCHIVED = "ARCHIVED"


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
    COLLECTION_ID = "collection_id"
    COLLECTION_GULAX_NAME = "collection_gulax_name"
    DESCRIPTION = "description"
    COLLECTION_ROLES = "collection_roles"
    CREATED_AT = "created_at"
    CREATED_BY = "created_by"
