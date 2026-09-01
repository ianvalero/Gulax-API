from fastapi import Request

import app.services as services

def get_tenant_service(request: Request) -> services.TenantService:
    return request.app.state.tenant_service

def get_knowledge_space_service(request: Request) -> services.KnowledgeSpaceService:
    return request.app.state.knowledge_space_service

def get_document_service(request: Request) -> services.DocumentService:
    return request.app.state.document_service

def get_document_version_service(request: Request) -> services.DocumentVersionService:
    return request.app.state.document_version_service

def get_ingestion_run_service(request: Request) -> services.IngestionRunService:
    return request.app.state.ingestion_run_service

def get_user_service(request: Request) -> services.UserService:
    return request.app.state.user_service

def get_retrieval_service(request: Request) -> services.RetrievalService:
    return request.app.state.retrieval_service