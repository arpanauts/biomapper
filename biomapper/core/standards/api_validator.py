"""API Method Validator for ensuring correct API client method usage."""

import inspect
import logging
from typing import Any, Dict, List, Optional, Callable, get_type_hints
from difflib import get_close_matches

logger = logging.getLogger(__name__)


class APIMethodValidator:
    """Validate API methods exist and have correct signatures."""
    
    @staticmethod
    def validate_method_exists(
        client: Any, 
        method_name: str,
        suggest_alternatives: bool = True
    ) -> bool:
        """
        Check if method exists on client.
        
        Args:
            client: API client object
            method_name: Method to check
            suggest_alternatives: Whether to suggest similar methods
            
        Returns:
            True if method exists
            
        Raises:
            AttributeError with helpful message if not
        """
        if not hasattr(client, method_name):
            available = [
                m for m in dir(client) 
                if not m.startswith('_') and callable(getattr(client, m, None))
            ]
            
            message = f"Method '{method_name}' not found on {client.__class__.__name__}"
            
            if suggest_alternatives:
                similar = APIMethodValidator.find_similar_methods(
                    method_name, available
                )
                if similar:
                    message += f"\nDid you mean one of: {similar}?"
                
            message += f"\nAvailable methods: {sorted(available)}"
            raise AttributeError(message)
        
        return True
    
    @staticmethod
    def find_similar_methods(target: str, available: List[str]) -> List[str]:
        """Find methods with similar names using difflib."""
        # Get close matches with cutoff of 0.6 similarity
        similar = get_close_matches(target, available, n=3, cutoff=0.6)
        
        # If no close matches, try partial matching
        if not similar:
            target_lower = target.lower()
            partial_matches = [
                m for m in available 
                if target_lower in m.lower() or m.lower() in target_lower
            ]
            similar = partial_matches[:3]
        
        return similar
    
    @staticmethod
    def validate_signature(
        client: Any,
        method_name: str,
        expected_params: Optional[Dict[str, type]] = None
    ) -> bool:
        """
        Validate method signature matches expectations.
        
        Args:
            client: API client object
            method_name: Method name to validate
            expected_params: Expected parameter types (optional)
            
        Returns:
            True if signature is valid
            
        Raises:
            ValueError if signature doesn't match
        """
        if not hasattr(client, method_name):
            raise AttributeError(f"Method '{method_name}' not found")
        
        method = getattr(client, method_name)
        if not callable(method):
            raise ValueError(f"'{method_name}' is not a callable method")
        
        if expected_params:
            sig = inspect.signature(method)
            actual_params = sig.parameters
            
            # Check for missing expected parameters
            missing = []
            mismatched = []
            
            for param_name, expected_type in expected_params.items():
                if param_name not in actual_params:
                    missing.append(param_name)
                else:
                    # Try to get type hints
                    try:
                        hints = get_type_hints(method)
                        if param_name in hints:
                            actual_type = hints[param_name]
                            if actual_type != expected_type:
                                mismatched.append(
                                    f"{param_name}: expected {expected_type}, got {actual_type}"
                                )
                    except Exception:
                        # Type hints not available
                        pass
            
            if missing or mismatched:
                error_msg = f"Signature mismatch for method '{method_name}':"
                if missing:
                    error_msg += f"\n  Missing parameters: {missing}"
                if mismatched:
                    error_msg += f"\n  Type mismatches: {mismatched}"
                raise ValueError(error_msg)
        
        return True
    
    @staticmethod
    def create_method_wrapper(
        client: Any,
        method_name: str,
        validate_before_call: bool = True
    ) -> Callable:
        """
        Create wrapper with validation and error handling.
        
        Args:
            client: API client object
            method_name: Method to wrap
            validate_before_call: Whether to validate before each call
            
        Returns:
            Wrapped method with validation
        """
        # Validate method exists
        APIMethodValidator.validate_method_exists(client, method_name)
        
        original_method = getattr(client, method_name)
        
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Wrapper function with validation and error handling."""
            if validate_before_call:
                # Re-validate method still exists (in case of dynamic changes)
                if not hasattr(client, method_name):
                    raise AttributeError(
                        f"Method '{method_name}' no longer exists on {client.__class__.__name__}"
                    )
            
            try:
                # Log the call
                logger.debug(
                    f"Calling {client.__class__.__name__}.{method_name} "
                    f"with args={args}, kwargs={kwargs}"
                )
                
                # Call the original method
                result = original_method(*args, **kwargs)
                
                # Log success
                logger.debug(
                    f"Successfully called {client.__class__.__name__}.{method_name}"
                )
                
                return result
                
            except AttributeError as e:
                # Method doesn't exist - provide helpful error
                available = [
                    m for m in dir(client) 
                    if not m.startswith('_') and callable(getattr(client, m, None))
                ]
                similar = APIMethodValidator.find_similar_methods(method_name, available)
                
                error_msg = (
                    f"Method '{method_name}' failed on {client.__class__.__name__}: {str(e)}"
                )
                if similar:
                    error_msg += f"\nDid you mean one of: {similar}?"
                
                logger.error(error_msg)
                raise AttributeError(error_msg) from e
                
            except TypeError as e:
                # Wrong arguments - provide signature help
                sig = inspect.signature(original_method)
                error_msg = (
                    f"Wrong arguments for {client.__class__.__name__}.{method_name}: {str(e)}\n"
                    f"Expected signature: {sig}"
                )
                logger.error(error_msg)
                raise TypeError(error_msg) from e
                
            except Exception as e:
                # Other errors - log and re-raise
                error_msg = (
                    f"Error calling {client.__class__.__name__}.{method_name}: "
                    f"{e.__class__.__name__}: {str(e)}"
                )
                logger.error(error_msg, exc_info=True)
                raise
        
        # Preserve original method metadata
        wrapper.__name__ = method_name
        wrapper.__doc__ = original_method.__doc__
        
        return wrapper
    
    @staticmethod
    def validate_client_interface(
        client: Any,
        required_methods: List[str],
        optional_methods: Optional[List[str]] = None
    ) -> Dict[str, bool]:
        """
        Validate that a client has all required methods.
        
        Args:
            client: API client to validate
            required_methods: Methods that must exist
            optional_methods: Methods that may exist
            
        Returns:
            Dict mapping method names to availability
            
        Raises:
            ValueError if any required methods are missing
        """
        results = {}
        missing_required = []
        
        # Check required methods
        for method in required_methods:
            if hasattr(client, method) and callable(getattr(client, method)):
                results[method] = True
            else:
                results[method] = False
                missing_required.append(method)
        
        # Check optional methods
        if optional_methods:
            for method in optional_methods:
                results[method] = (
                    hasattr(client, method) and 
                    callable(getattr(client, method))
                )
        
        # Raise error if missing required methods
        if missing_required:
            available = [
                m for m in dir(client) 
                if not m.startswith('_') and callable(getattr(client, m, None))
            ]
            
            error_msg = (
                f"Client {client.__class__.__name__} is missing required methods: "
                f"{missing_required}\n"
                f"Available methods: {sorted(available)}"
            )
            
            # Suggest alternatives for each missing method
            suggestions = {}
            for missing in missing_required:
                similar = APIMethodValidator.find_similar_methods(missing, available)
                if similar:
                    suggestions[missing] = similar
            
            if suggestions:
                error_msg += "\n\nDid you mean:"
                for missing, similar in suggestions.items():
                    error_msg += f"\n  {missing} -> {similar}"
            
            raise ValueError(error_msg)
        
        return results