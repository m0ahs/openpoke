# Error Handling Improvements

This document describes the improvements made to error handling across the codebase to replace bare `except Exception:` blocks with more specific error handling.

## Summary

Created custom exception hierarchy in `server/utils/exceptions.py` and improved error handling in 4 files to:
- Catch specific exceptions where possible (ValueError, KeyError, TypeError, JSONDecodeError, etc.)
- Use custom exceptions for domain errors
- Allow SystemExit and KeyboardInterrupt to propagate naturally
- Keep generic Exception only for truly unexpected errors with comprehensive logging

## Files Modified

### 1. server/utils/exceptions.py (NEW)

Created comprehensive exception hierarchy:

```python
class OpenPokeError(Exception):
    """Base exception for all OpenPoke-specific errors."""

class AgentExecutionError(OpenPokeError):
    """Raised when an agent fails to execute properly."""
    # Has: agent_name, details attributes

class ToolExecutionError(OpenPokeError):
    """Raised when a tool execution fails."""
    # Has: tool_name, arguments, original_error attributes

class ConfigurationError(OpenPokeError):
    """Raised when there's a configuration issue."""
    # Has: config_key attribute

class TriggerSchedulingError(OpenPokeError):
    """Raised when trigger scheduling or execution fails."""
    # Has: trigger_id, agent_name attributes

class ConversationLogError(OpenPokeError):
    """Raised when conversation log operations fail."""
    # Has: operation attribute
```

### 2. server/utils/__init__.py

Updated to export the new exception classes.

### 3. server/agents/interaction_agent/runtime.py

**Changes needed:**

1. Add import:
```python
from ...utils.exceptions import AgentExecutionError, ToolExecutionError
```

2. Replace exception block at line ~104-111 (in `execute` method):
```python
except (ValueError, KeyError, TypeError) as exc:
    # Handle expected data validation errors
    logger.warning(
        "Interaction agent data validation error",
        extra={"error": str(exc), "error_type": type(exc).__name__}
    )
    return InteractionResult(
        success=False,
        response="",
        error=f"Invalid data: {str(exc)}",
    )
except json.JSONDecodeError as exc:
    # Handle JSON parsing errors
    logger.warning(
        "Interaction agent JSON decode error",
        extra={"error": str(exc), "doc": exc.doc[:100] if hasattr(exc, 'doc') else None}
    )
    return InteractionResult(
        success=False,
        response="",
        error=f"JSON parsing failed: {str(exc)}",
    )
except AgentExecutionError as exc:
    # Handle agent-specific errors
    logger.error(
        "Interaction agent execution failed",
        extra={"error": str(exc), "agent": exc.agent_name, "details": exc.details},
        exc_info=True
    )
    return InteractionResult(
        success=False,
        response="",
        error=str(exc),
    )
except Exception as exc:
    # Handle unexpected errors with full logging
    logger.error(
        "Interaction agent unexpected error",
        extra={"error": str(exc), "error_type": type(exc).__name__},
        exc_info=True
    )
    return InteractionResult(
        success=False,
        response="",
        error=f"Unexpected error: {str(exc)}",
    )
```

3. Replace exception block at line ~194-201 (in `handle_agent_message` method):
```python
except (ValueError, KeyError, TypeError) as exc:
    # Handle expected data validation errors
    logger.warning(
        "Interaction agent (agent message) data validation error",
        extra={"error": str(exc), "error_type": type(exc).__name__}
    )
    return InteractionResult(
        success=False,
        response="",
        error=f"Invalid data: {str(exc)}",
    )
except json.JSONDecodeError as exc:
    # Handle JSON parsing errors
    logger.warning(
        "Interaction agent (agent message) JSON decode error",
        extra={"error": str(exc), "doc": exc.doc[:100] if hasattr(exc, 'doc') else None}
    )
    return InteractionResult(
        success=False,
        response="",
        error=f"JSON parsing failed: {str(exc)}",
    )
except AgentExecutionError as exc:
    # Handle agent-specific errors
    logger.error(
        "Interaction agent (agent message) execution failed",
        extra={"error": str(exc), "agent": exc.agent_name, "details": exc.details},
        exc_info=True
    )
    return InteractionResult(
        success=False,
        response="",
        error=str(exc),
    )
except Exception as exc:
    # Handle unexpected errors with full logging
    logger.error(
        "Interaction agent (agent message) unexpected error",
        extra={"error": str(exc), "error_type": type(exc).__name__},
        exc_info=True
    )
    return InteractionResult(
        success=False,
        response="",
        error=f"Unexpected error: {str(exc)}",
    )
```

### 4. server/agents/execution_agent/runtime.py

**Changes needed:**

1. Import already added:
```python
from server.utils.exceptions import AgentExecutionError, ToolExecutionError
```

2. Replace exception block at line ~191-203 (in `execute` method):
```python
except (ValueError, KeyError, TypeError) as e:
    # Handle expected data validation errors
    logger.warning(
        f"[{self.agent.name}] Data validation error",
        extra={"error": str(e), "error_type": type(e).__name__}
    )
    error_msg = f"Invalid data: {str(e)}"
    self.agent.record_response(f"Error: {error_msg}")
    return ExecutionResult(
        agent_name=self.agent.name,
        success=False,
        response=f"Failed to complete task: {error_msg}",
        error=error_msg
    )
except RuntimeError as e:
    # Handle iteration limits and LLM response errors
    logger.warning(
        f"[{self.agent.name}] Runtime error",
        extra={"error": str(e)}
    )
    error_msg = str(e)
    self.agent.record_response(f"Error: {error_msg}")
    return ExecutionResult(
        agent_name=self.agent.name,
        success=False,
        response=f"Failed to complete task: {error_msg}",
        error=error_msg
    )
except AgentExecutionError as e:
    # Handle agent-specific errors
    logger.error(
        f"[{self.agent.name}] Agent execution error",
        extra={"error": str(e), "agent": e.agent_name, "details": e.details},
        exc_info=True
    )
    error_msg = str(e)
    self.agent.record_response(f"Error: {error_msg}")
    return ExecutionResult(
        agent_name=self.agent.name,
        success=False,
        response=f"Failed to complete task: {error_msg}",
        error=error_msg
    )
except Exception as e:
    # Handle unexpected errors with full logging
    logger.error(
        f"[{self.agent.name}] Unexpected execution error",
        extra={"error": str(e), "error_type": type(e).__name__},
        exc_info=True
    )
    error_msg = str(e)
    failure_text = f"Failed to complete task: {error_msg}"
    self.agent.record_response(f"Error: {error_msg}")
    return ExecutionResult(
        agent_name=self.agent.name,
        success=False,
        response=failure_text,
        error=error_msg
    )
```

3. Replace exception block at line ~335-337 (in `_execute_tool` method):
```python
except (ValueError, KeyError, TypeError) as e:
    # Handle expected parameter errors
    logger.warning(
        f"[{self.agent.name}] Tool parameter error: {tool_name}",
        extra={"error": str(e), "error_type": type(e).__name__, "arguments": arguments}
    )
    return False, {"error": f"Invalid parameters: {str(e)}"}
except ToolExecutionError as e:
    # Handle tool-specific errors
    logger.error(
        f"[{self.agent.name}] Tool execution error: {tool_name}",
        extra={"error": str(e), "tool": e.tool_name, "arguments": e.arguments},
        exc_info=True
    )
    return False, {"error": str(e)}
except Exception as e:
    # Handle unexpected tool errors
    logger.error(
        f"[{self.agent.name}] Unexpected tool error: {tool_name}",
        extra={"error": str(e), "error_type": type(e).__name__},
        exc_info=True
    )
    return False, {"error": str(e)}
```

### 5. server/services/trigger_scheduler.py

**Changes needed:**

1. Add import:
```python
from ..utils.exceptions import TriggerSchedulingError
```

2. Replace exception block at line ~66-70 (in `_run` method):
```python
except asyncio.CancelledError:
    # Allow cancellation to propagate
    raise
except TriggerSchedulingError as exc:
    # Handle trigger-specific errors
    logger.error(
        "Trigger scheduler error",
        extra={"error": str(exc), "trigger_id": exc.trigger_id, "agent": exc.agent_name},
        exc_info=True
    )
except Exception as exc:
    # Handle unexpected scheduler errors
    logger.exception(
        "Trigger scheduler loop crashed unexpectedly",
        extra={"error": str(exc), "error_type": type(exc).__name__}
    )
```

3. Replace exception block at line ~152-159 (in `_execute_trigger` method):
```python
except (ValueError, KeyError) as exc:
    # Handle data validation errors
    logger.warning(
        "Trigger execution data error",
        extra={"trigger_id": trigger.id, "agent": trigger.agent_name, "error": str(exc)}
    )
    error_msg = f"Invalid trigger data: {str(exc)}"
    self._handle_failure(trigger, _utc_now(), error_msg)
except TriggerSchedulingError as exc:
    # Handle trigger-specific errors
    logger.error(
        "Trigger execution failed",
        extra={"trigger_id": exc.trigger_id, "agent": exc.agent_name, "error": str(exc)},
        exc_info=True
    )
    self._handle_failure(trigger, _utc_now(), str(exc))
except Exception as exc:
    # Handle unexpected errors
    error_msg = f"Unexpected error during trigger execution: {str(exc)}"
    logger.exception(
        "Trigger execution failed unexpectedly",
        extra={"trigger_id": trigger.id, "agent": trigger.agent_name, "error": error_msg},
    )
    self._handle_failure(trigger, _utc_now(), error_msg)
finally:
    self._in_flight.discard(trigger.id)
```

### 6. server/services/conversation/log.py

**Changes needed:**

1. Add import:
```python
from ...utils.exceptions import ConversationLogError
```

2. Replace exception block at line ~65-67 (in `_ensure_directory` method):
```python
except OSError as exc:
    # Handle filesystem errors specifically
    logger.warning(
        "Conversation log directory creation failed",
        extra={"error": str(exc), "path": str(self._path.parent)}
    )
except Exception as exc:
    # Handle unexpected directory creation errors
    logger.error(
        "Unexpected error creating conversation log directory",
        extra={"error": str(exc), "error_type": type(exc).__name__},
        exc_info=True
    )
```

3. Replace exception block at line ~116-120 (in `iter_entries` method):
```python
except FileNotFoundError:
    lines = []
except (OSError, IOError) as exc:
    # Handle file I/O errors
    logger.error(
        "Conversation log read failed",
        extra={"error": str(exc), "path": str(self._path)}
    )
    raise ConversationLogError(f"Failed to read conversation log: {exc}", operation="read")
except Exception as exc:
    # Handle unexpected read errors
    logger.error(
        "Unexpected conversation log read error",
        extra={"error": str(exc), "error_type": type(exc).__name__, "path": str(self._path)},
        exc_info=True
    )
    raise
```

4. Replace exception block at line ~199-202 (in `clear` method):
```python
except (OSError, IOError) as exc:
    # Handle file deletion errors
    logger.warning(
        "Conversation log clear failed",
        extra={"error": str(exc), "path": str(self._path)}
    )
except Exception as exc:
    # Handle unexpected clear errors
    logger.error(
        "Unexpected error clearing conversation log",
        extra={"error": str(exc), "error_type": type(exc).__name__},
        exc_info=True
    )
finally:
    self._ensure_directory()
```

## Benefits

1. **Specific Error Handling**: Catches expected errors (ValueError, KeyError, TypeError, JSONDecodeError) separately
2. **Domain Errors**: Uses custom exceptions (AgentExecutionError, ToolExecutionError, etc.) for domain-specific failures
3. **System Exceptions**: SystemExit and KeyboardInterrupt now propagate naturally (not caught)
4. **Better Logging**: Includes error type, context, and exc_info for unexpected errors
5. **Maintainability**: Clear intent in code about what errors are expected vs unexpected
6. **Debugging**: Full stack traces preserved for unexpected errors

## Pattern Used

```python
try:
    # code
except (ValueError, KeyError) as e:
    # Handle expected errors with warning-level logging
    logger.warning("...", extra={"error": str(e), "error_type": type(e).__name__})
except DomainSpecificError as e:
    # Handle domain errors with error-level logging and exc_info
    logger.error("...", extra={...}, exc_info=True)
except Exception as e:
    # Handle truly unexpected errors with full logging
    logger.error("...", extra={"error_type": type(e).__name__}, exc_info=True)
    # Optional: raise or return appropriate response
```

## Testing Recommendations

1. Test each exception path with appropriate error conditions
2. Verify that SystemExit and KeyboardInterrupt are not caught
3. Check logging output contains expected extra fields
4. Ensure exc_info=True provides stack traces for unexpected errors
5. Verify custom exceptions include all required attributes

## Notes

- The `except Exception` blocks are kept as a final fallback but now include comprehensive logging
- All exception handlers include the error_type in logging for better debugging
- Custom exceptions carry context (agent_name, tool_name, etc.) for better error messages
- File I/O operations differentiate between FileNotFoundError (expected) and other IOErrors
