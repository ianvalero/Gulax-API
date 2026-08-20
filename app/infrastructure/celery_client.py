import logging
from celery.result import AsyncResult

from app.celery_workers.celery_app import celery_app


class CeleryClient:
    def __init__(self):
        self.logger = logging.getLogger(f"app.{__name__}")
        self.celery_app = celery_app
        self.logger.info("Celery Client initialized")

    def get_task_status(self, task_id: str) -> dict:
        """
        Retrieve the execution status and result of a specific asynchronous task.

        This method interacts with the Celery task processing system to fetch the
        current execution status and result of a task identified by its ID.

        :param task_id: The unique identifier for the task whose status and result
            need to be retrieved.
        :type task_id: str
        :return: A dictionary containing the task's unique ID, its current status,
            and its result if the task is completed. If the task result is not yet
            available, the result will be None.
        :rtype: dict
        :raises Exception: If there is an error while fetching the task status.
        """
        self.logger.info(f"Getting status for task {task_id}")
        try:
            result = AsyncResult(task_id, app=celery_app)
            return {
                "task_id": task_id,
                "status": result.status,
                "result": result.result if result.ready() else None,
            }
        except Exception as e:
            self.logger.error(f"Error getting task status for {task_id}")
            self.logger.exception(e)
            raise

    def update_document_version(self, document_version_id: int):
        """
        Updates the specified document version by initiating a Celery task to
        process the document. Logs the status of the task initiation and returns
        the task identifier upon successful submission.

        :param document_version: The DocumentVersionDB object representing the
            document version to be processed.
        :type document_version: DocumentVersionDB
        :return: The identifier of the Celery task initiated for processing the
            document version.
        :rtype: str
        :raises Exception: If there is an error while sending the task to
            Celery for processing.
        """
        self.logger.info(f"Updating document version {document_version_id} in Celery task")
        try:
            task = celery_app.send_task(
                "tasks.process_document_version",
                kwargs={"document_version_id": document_version_id}
            )
            self.logger.info(f"Document version {document_version_id} update task sent to Celery successfully")
            return task.id
        except Exception as e:
            self.logger.error(f"Error sending document version update task for {document_version_id} to Celery")
            self.logger.exception(e)
            raise

    def revoke_task(self, task_id: str) -> bool:
        """
        Revoke a task identified by its task ID and terminate its execution if running.

        :param task_id: The unique identifier of the task to be revoked.
        :type task_id: str
        :return: A boolean indicating whether the task was successfully revoked.
        :rtype: bool
        """
        AsyncResult(task_id, app=self.celery_app).revoke(terminate=True)
        self.logger.info(f"Task revoked: {task_id}")
        return True