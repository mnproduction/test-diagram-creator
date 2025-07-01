import importlib
import inspect
import logging
from pathlib import Path

from .engine import DiagramEngine
from .tools.base_tool import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Manages the registration and retrieval of tools for diagram generation.

    Implements dynamic tool discovery with robust error handling following
    the hybrid simple-robust approach from the creative phase design.
    """

    def __init__(self, engine: DiagramEngine):
        self.engine = engine
        self._tools: dict[str, BaseTool] = {}
        self._discovery_errors: dict[str, str] = {}

        # Perform dynamic tool discovery
        self._discover_and_register_tools()

        logger.info(
            f"ToolRegistry initialized with {len(self._tools)} tools: "
            f"{list(self._tools.keys())}"
        )

        if self._discovery_errors:
            logger.warning(
                f"Tool discovery encountered {len(self._discovery_errors)} errors: "
                f"{list(self._discovery_errors.keys())}"
            )

    def _discover_and_register_tools(self):
        """
        Discover and register all BaseTool subclasses from the tools directory.

        Implements the hybrid simple-robust approach:
        - Single discovery during initialization with caching
        - Graceful error handling without system crashes
        - Both class structure and instance validation
        """
        tools_discovered = self._discover_tools()

        for tool_name, tool_class in tools_discovered.items():
            try:
                # Validate and instantiate the tool
                self._validate_and_register_tool(tool_class)

            except Exception as e:
                self._discovery_errors[tool_name] = str(e)
                logger.error(
                    f"Failed to register tool '{tool_name}': {e}", exc_info=True
                )

    def _discover_tools(self) -> dict[str, type[BaseTool]]:
        """
        Scan tools directory and return all BaseTool subclasses.

        Returns:
            Dict mapping tool_name -> tool_class for all discovered tools
        """
        discovered_tools = {}

        # Get the tools directory path
        current_dir = Path(__file__).parent
        tools_dir = current_dir / "tools"

        if not tools_dir.exists():
            logger.warning(f"Tools directory not found: {tools_dir}")
            return discovered_tools

        logger.debug(f"Scanning tools directory: {tools_dir}")

        # Scan Python files in the tools directory
        for python_file in tools_dir.glob("*.py"):
            if python_file.name.startswith("__"):
                continue  # Skip __init__.py and __pycache__

            try:
                module_name = f"src.diagram.tools.{python_file.stem}"
                self._scan_module_for_tools(module_name, discovered_tools)

            except Exception as e:
                logger.error(
                    f"Failed to scan module '{python_file}': {e}", exc_info=True
                )
                continue

        logger.debug(f"Discovered {len(discovered_tools)} tool classes")
        return discovered_tools

    def _scan_module_for_tools(
        self, module_name: str, discovered_tools: dict[str, type[BaseTool]]
    ):
        """
        Scan a specific module for BaseTool subclasses.

        Args:
            module_name: Full module name to import and scan
            discovered_tools: Dictionary to add discovered tools to
        """
        try:
            # Import the module
            module = importlib.import_module(module_name)

            # Find all BaseTool subclasses in the module
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (
                    obj is not BaseTool
                    and issubclass(obj, BaseTool)
                    and obj.__module__ == module_name
                ):
                    # Validate the tool class structure
                    if self._validate_tool_class(obj):
                        tool_name = getattr(obj, "name", name.lower())
                        discovered_tools[tool_name] = obj
                        logger.debug(f"Discovered tool class: {name} -> {tool_name}")
                    else:
                        logger.warning(f"Tool class '{name}' failed validation")

        except ImportError as e:
            logger.error(f"Cannot import module '{module_name}': {e}")
            raise
        except Exception as e:
            logger.error(f"Error scanning module '{module_name}': {e}")
            raise

    def _validate_tool_class(self, tool_class: type[BaseTool]) -> bool:
        """
        Validate that a tool class meets the BaseTool interface requirements.

        Args:
            tool_class: The tool class to validate

        Returns:
            bool: True if the tool class is valid, False otherwise
        """
        try:
            # Check required class attributes
            if not hasattr(tool_class, "name") or not isinstance(tool_class.name, str):
                logger.warning(
                    f"{tool_class.__name__} missing or invalid 'name' attribute"
                )
                return False

            if not hasattr(tool_class, "description") or not isinstance(
                tool_class.description, str
            ):
                logger.warning(
                    f"{tool_class.__name__} missing or invalid 'description' attribute"
                )
                return False

            # Check that execute method exists and is properly defined
            if not hasattr(tool_class, "execute"):
                logger.warning(f"{tool_class.__name__} missing 'execute' method")
                return False

            # Verify execute method signature (should be async)
            execute_method = tool_class.execute
            if not inspect.iscoroutinefunction(execute_method):
                logger.warning(f"{tool_class.__name__}.execute is not an async method")
                return False

            return True

        except Exception as e:
            logger.error(f"Error validating tool class {tool_class.__name__}: {e}")
            return False

    def _validate_and_register_tool(self, tool_class: type[BaseTool]):
        """
        Validate and register a single tool instance.

        Args:
            tool_class: The tool class to instantiate and register
        """
        # Instantiate the tool
        try:
            tool_instance = tool_class()
        except Exception as e:
            raise RuntimeError(
                f"Failed to instantiate {tool_class.__name__}: {e}"
            ) from e

        # Validate the instance
        if not isinstance(tool_instance, BaseTool):
            raise TypeError(f"{tool_class.__name__} instance is not a BaseTool")

        # Check for name conflicts
        tool_name = tool_instance.name
        if tool_name in self._tools:
            logger.warning(
                f"Tool name conflict: '{tool_name}' already registered. Overwriting."
            )

        # Register the tool
        self._tools[tool_name] = tool_instance
        logger.debug(f"Registered tool: {tool_name} ({tool_class.__name__})")

    def get_tool(self, name: str) -> BaseTool:
        """
        Retrieve a tool by its name.

        Args:
            name: The name of the tool to retrieve

        Returns:
            BaseTool: The requested tool instance

        Raises:
            KeyError: If the tool is not found
        """
        tool = self._tools.get(name)
        if not tool:
            available_tools = list(self._tools.keys())
            raise KeyError(
                f"Tool '{name}' not found in registry. "
                f"Available tools: {available_tools}"
            )
        return tool

    def list_tools(self) -> dict[str, str]:
        """
        List all registered tools and their descriptions.

        Returns:
            Dict[str, str]: Mapping of tool names to descriptions
        """
        return {name: tool.description for name, tool in self._tools.items()}

    def get_discovery_errors(self) -> dict[str, str]:
        """
        Get any errors that occurred during tool discovery.

        Returns:
            Dict[str, str]: Mapping of failed tool names to error messages
        """
        return self._discovery_errors.copy()

    def get_tool_count(self) -> int:
        """
        Get the number of successfully registered tools.

        Returns:
            int: Number of registered tools
        """
        return len(self._tools)
