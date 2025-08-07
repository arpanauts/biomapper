"""Safe expression evaluator for YAML strategy conditions.

This module provides a safe expression evaluator that allows controlled evaluation
of conditions in YAML strategies without allowing arbitrary code execution.
"""

import ast
import operator
import re
from typing import Any, Dict, List, Union
import json


class ExpressionError(Exception):
    """Error raised during expression evaluation."""

    pass


class SafeExpressionEvaluator:
    """
    Safe expression evaluator for YAML conditions.

    Only allows specific operations, no arbitrary code execution.
    Supports:
    - Variable resolution: ${steps.baseline.metrics.score}
    - Arithmetic: +, -, *, /
    - Comparison: ==, !=, <, <=, >, >=
    - Logical: and, or, not
    - Ternary: condition ? true_value : false_value
    - Function calls: limited set of safe functions
    """

    # Allowed operators
    OPERATORS = {
        # Arithmetic
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.FloorDiv: operator.floordiv,
        ast.Mod: operator.mod,
        # Comparison
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        # Logical
        ast.And: lambda *args: all(args),
        ast.Or: lambda *args: any(args),
        ast.Not: operator.not_,
        # Bitwise (for flags)
        ast.BitAnd: operator.and_,
        ast.BitOr: operator.or_,
        ast.BitXor: operator.xor,
    }

    # Safe built-in functions
    SAFE_FUNCTIONS = {
        "len": len,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "abs": abs,
        "min": min,
        "max": max,
        "sum": sum,
        "round": round,
        "any": any,
        "all": all,
    }

    # Safe context methods
    SAFE_METHODS = {
        "has_api_key": lambda ctx, key: key in ctx.get("api_keys", {}),
        "has_file": lambda ctx, path: ctx.get("file_system", {}).get(
            "exists", lambda p: False
        )(path),
        "get_env": lambda ctx, key, default=None: ctx.get("env", {}).get(key, default),
        "is_defined": lambda ctx, path: ctx.get(path) is not None,
    }

    def __init__(self, context: Dict[str, Any]):
        """
        Initialize evaluator with execution context.

        Args:
            context: Execution context containing variables, steps results, etc.
        """
        self.context = context
        self._variable_cache = {}

    def evaluate(self, expression: str) -> Any:
        """
        Safely evaluate an expression.

        Examples:
            "${steps.baseline.metrics.score} > 0.8"
            "${parameters.threshold} * 0.9"
            "${context.has_data} and ${parameters.enabled}"
            "${dataset_size} > 1000 ? 0.9 : 1.0"

        Args:
            expression: Expression to evaluate

        Returns:
            Result of expression evaluation

        Raises:
            ExpressionError: If expression is invalid or unsafe
        """
        if not expression:
            return True

        try:
            # Handle ternary operator (? :) by converting to Python syntax
            expression = self._convert_ternary(expression)

            # Resolve ${...} variable references
            resolved = self._resolve_variables(expression)

            # Parse and evaluate safely
            tree = ast.parse(resolved, mode="eval")

            # Validate AST for safety
            self._validate_ast(tree)

            # Evaluate the expression
            return self._eval_node(tree.body)

        except SyntaxError as e:
            raise ExpressionError(f"Invalid expression syntax: {expression}: {e}")
        except Exception as e:
            raise ExpressionError(f"Error evaluating expression: {expression}: {e}")

    def _convert_ternary(self, expression: str) -> str:
        """Convert ternary operator (? :) to Python if/else syntax."""
        # Pattern: condition ? true_value : false_value
        # Convert to: true_value if condition else false_value
        pattern = r"([^?]+)\?([^:]+):(.+)"
        match = re.match(pattern, expression.strip())

        if match:
            condition, true_val, false_val = match.groups()
            return f"({true_val.strip()}) if ({condition.strip()}) else ({false_val.strip()})"

        return expression

    def _resolve_variables(self, expression: str) -> str:
        """Resolve ${...} variable references."""
        pattern = r"\$\{([^}]+)\}"

        def replacer(match):
            path = match.group(1).strip()

            # Don't use cache - always get fresh value
            value = self._get_nested_value(path)

            # Convert value to Python literal
            if isinstance(value, str):
                return repr(value)
            elif isinstance(value, bool):
                return "True" if value else "False"
            elif value is None:
                return "None"
            else:
                return str(value)

        return re.sub(pattern, replacer, expression)

    def _get_nested_value(self, path: str) -> Any:
        """
        Get nested value from context using dot notation.

        Supports:
        - Dot notation: steps.baseline.metrics.score
        - Array indexing: datasets[0].name
        - Method calls: context.has_api_key('OPENAI')
        - Default values: env.DEBUG:-false
        """
        # Handle default values (path:-default)
        default = None
        if ":-" in path:
            path, default = path.split(":-", 1)
            # Parse default value
            try:
                default = json.loads(default)
            except:
                # Keep as string if not valid JSON
                pass

        # Handle method calls
        if "(" in path and ")" in path:
            return self._handle_method_call(path)

        # Split path into parts
        parts = self._parse_path(path)

        # Navigate through context
        value = self.context
        for part in parts:
            if isinstance(part, int):
                # Array index
                if isinstance(value, (list, tuple)) and 0 <= part < len(value):
                    value = value[part]
                else:
                    return default
            else:
                # Dictionary key or attribute
                if isinstance(value, dict):
                    value = value.get(part, default)
                    if value == default:
                        return default
                elif hasattr(value, part):
                    value = getattr(value, part)
                else:
                    return default

        return value

    def _parse_path(self, path: str) -> List[Union[str, int]]:
        """Parse path into parts, handling array indices."""
        parts = []
        current = ""

        i = 0
        while i < len(path):
            char = path[i]
            if char == ".":
                if current:
                    parts.append(current)
                    current = ""
            elif char == "[":
                if current:
                    parts.append(current)
                    current = ""
                # Find closing bracket
                j = path.find("]", i)
                if j == -1:
                    raise ExpressionError(f"Unclosed bracket in path: {path}")
                index_str = path[i + 1 : j]
                try:
                    parts.append(int(index_str))
                except ValueError:
                    raise ExpressionError(f"Invalid array index: {index_str}")
                i = j
            else:
                current += char
            i += 1

        if current:
            parts.append(current)

        return parts

    def _handle_method_call(self, path: str) -> Any:
        """Handle method calls in expressions."""
        # Parse method call: object.method(args)
        match = re.match(r"([^(]+)\.([^(]+)\(([^)]*)\)", path)
        if not match:
            # Maybe it's a global function
            match = re.match(r"([^(]+)\(([^)]*)\)", path)
            if match:
                func_name, args_str = match.groups()
                if func_name in self.SAFE_METHODS:
                    args = self._parse_arguments(args_str)
                    return self.SAFE_METHODS[func_name](self.context, *args)
                else:
                    raise ExpressionError(f"Unknown function: {func_name}")
            raise ExpressionError(f"Invalid method call: {path}")

        obj_path, method_name, args_str = match.groups()

        # Get the object
        obj = self._get_nested_value(obj_path) if obj_path else self.context

        # Parse arguments
        args = self._parse_arguments(args_str)

        # Call method
        if hasattr(obj, method_name):
            method = getattr(obj, method_name)
            if callable(method):
                return method(*args)
            else:
                raise ExpressionError(f"{method_name} is not a method")
        else:
            raise ExpressionError(f"Object has no method: {method_name}")

    def _parse_arguments(self, args_str: str) -> List[Any]:
        """Parse method arguments."""
        if not args_str.strip():
            return []

        args = []
        for arg in args_str.split(","):
            arg = arg.strip()
            if arg.startswith("'") or arg.startswith('"'):
                # String literal
                args.append(arg[1:-1])
            elif arg in ("True", "true"):
                args.append(True)
            elif arg in ("False", "false"):
                args.append(False)
            elif arg in ("None", "null"):
                args.append(None)
            else:
                # Try to parse as number
                try:
                    if "." in arg:
                        args.append(float(arg))
                    else:
                        args.append(int(arg))
                except ValueError:
                    # Treat as string
                    args.append(arg)

        return args

    def _validate_ast(self, tree: ast.AST) -> None:
        """Validate AST for safety - no dangerous operations."""
        for node in ast.walk(tree):
            # Disallow imports
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise ExpressionError("Import statements are not allowed")

            # Disallow function definitions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                raise ExpressionError("Function/class definitions are not allowed")

            # Disallow exec/eval
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("exec", "eval", "compile", "__import__"):
                        raise ExpressionError(f"Dangerous function: {node.func.id}")

            # Disallow attribute access to private/dunder attributes
            if isinstance(node, ast.Attribute):
                if node.attr.startswith("_"):
                    raise ExpressionError(
                        f"Private attribute access not allowed: {node.attr}"
                    )

    def _eval_node(self, node: ast.AST) -> Any:
        """Recursively evaluate AST node safely."""
        if isinstance(node, ast.Constant):
            return node.value

        elif isinstance(node, ast.Name):
            # Variable reference
            if node.id == "True":
                return True
            elif node.id == "False":
                return False
            elif node.id == "None":
                return None
            else:
                # Look up in context
                return self.context.get(node.id)

        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            op_func = self.OPERATORS.get(type(node.op))
            if op_func:
                return op_func(operand)
            else:
                raise ExpressionError(
                    f"Unsupported unary operator: {type(node.op).__name__}"
                )

        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            op_func = self.OPERATORS.get(type(node.op))
            if op_func:
                return op_func(left, right)
            else:
                raise ExpressionError(
                    f"Unsupported binary operator: {type(node.op).__name__}"
                )

        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator)
                op_func = self.OPERATORS.get(type(op))
                if op_func:
                    if not op_func(left, right):
                        return False
                else:
                    raise ExpressionError(
                        f"Unsupported comparison operator: {type(op).__name__}"
                    )
                left = right
            return True

        elif isinstance(node, ast.BoolOp):
            values = [self._eval_node(v) for v in node.values]
            op_func = self.OPERATORS.get(type(node.op))
            if op_func:
                return op_func(values)
            else:
                raise ExpressionError(
                    f"Unsupported boolean operator: {type(node.op).__name__}"
                )

        elif isinstance(node, ast.IfExp):
            # Ternary operator (x if condition else y)
            condition = self._eval_node(node.test)
            if condition:
                return self._eval_node(node.body)
            else:
                return self._eval_node(node.orelse)

        elif isinstance(node, ast.Call):
            # Function call
            if isinstance(node.func, ast.Name):
                func_name = node.func.id
                if func_name in self.SAFE_FUNCTIONS:
                    args = [self._eval_node(arg) for arg in node.args]
                    return self.SAFE_FUNCTIONS[func_name](*args)
                else:
                    raise ExpressionError(f"Unknown function: {func_name}")
            else:
                raise ExpressionError("Complex function calls not supported")

        elif isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]

        elif isinstance(node, ast.Dict):
            keys = [self._eval_node(k) for k in node.keys]
            values = [self._eval_node(v) for v in node.values]
            return dict(zip(keys, values))

        elif isinstance(node, ast.Subscript):
            # Array/dict subscript: obj[key]
            obj = self._eval_node(node.value)
            if isinstance(node.slice, ast.Constant):
                key = node.slice.value
            else:
                key = self._eval_node(node.slice)

            try:
                return obj[key]
            except (KeyError, IndexError, TypeError):
                return None

        else:
            raise ExpressionError(f"Unsupported node type: {type(node).__name__}")


class ConditionEvaluator:
    """High-level condition evaluator using SafeExpressionEvaluator."""

    def __init__(self, context: Dict[str, Any]):
        """Initialize with execution context."""
        self.context = context
        self.evaluator = SafeExpressionEvaluator(context)

    def __setattr__(self, name: str, value: Any):
        """Override setattr to ensure evaluator updates when context changes."""
        super().__setattr__(name, value)
        if name == "context" and hasattr(self, "evaluator"):
            # Re-create evaluator with new context
            self.evaluator = SafeExpressionEvaluator(value)

    def evaluate_condition(self, condition: Union[str, Dict[str, Any]]) -> bool:
        """
        Evaluate a condition from YAML strategy.

        Args:
            condition: Either a string expression or a Condition dict

        Returns:
            True if condition is met, False otherwise
        """
        if condition is None:
            return True

        if isinstance(condition, str):
            # Simple expression
            return bool(self.evaluator.evaluate(condition))

        elif isinstance(condition, dict):
            condition_type = condition.get("type", "simple")

            if condition_type == "simple":
                expr = condition.get("expression")
                return bool(self.evaluator.evaluate(expr)) if expr else True

            elif condition_type == "all":
                # All conditions must be true (AND)
                all_conditions = condition.get("all", [])
                return all(self.evaluate_condition(c) for c in all_conditions)

            elif condition_type == "any":
                # At least one condition must be true (OR)
                any_conditions = condition.get("any", [])
                return any(self.evaluate_condition(c) for c in any_conditions)

            else:
                raise ExpressionError(f"Unknown condition type: {condition_type}")

        else:
            raise ExpressionError(f"Invalid condition type: {type(condition)}")

    def update_context(self, updates: Dict[str, Any]) -> None:
        """Update the execution context."""
        self.context.update(updates)

    def set_variable(self, name: str, value: Any) -> None:
        """Set a variable in the context."""
        if "variables" not in self.context:
            self.context["variables"] = {}
        self.context["variables"][name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get a variable from the context."""
        return self.context.get("variables", {}).get(name, default)
