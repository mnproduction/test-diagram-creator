# src/core/exceptions.py


class DiagramCreatorException(Exception):
    """Base exception for all application-specific errors."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class AgentException(DiagramCreatorException):
    """Base exception for errors related to the agent domain."""

    pass


class DiagramException(DiagramCreatorException):
    """Base exception for errors related to the diagram generation domain."""

    pass


class ValidationException(DiagramCreatorException):
    """Base exception for errors related to the validation domain."""

    pass


class TemplateException(DiagramCreatorException):
    """Base exception for errors related to the template domain."""

    pass


class ApiException(DiagramCreatorException):
    """Base exception for errors related to the API domain."""

    pass


class InfrastructureException(DiagramCreatorException):
    """Base exception for errors related to the infrastructure domain."""

    pass


class ContextManagementException(DiagramException):
    """Raised for errors during diagram context management (e.g., nested clusters)."""

    pass


class RenderingException(DiagramException):
    """Raised for errors during the final diagram rendering process."""

    pass
