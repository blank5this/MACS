"""Calculator tool for MACS."""

from typing import Any, Dict, Union, List
import ast
import operator
import math


class CalculatorTool:
    """Tool for performing calculations.

    Supports:
    - Basic arithmetic (+, -, *, /, **, %)
    - Mathematical functions (sin, cos, sqrt, log, etc.)
    - Expression evaluation
    - Unit conversions
    """

    # Supported operators
    OPS = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
        ast.Mod: operator.mod,
        ast.USub: operator.neg,
    }

    # Math functions available
    MATH_FUNCTIONS = {
        "sin": math.sin,
        "cos": math.cos,
        "tan": math.tan,
        "sqrt": math.sqrt,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
        "floor": math.floor,
        "ceil": math.ceil,
        "abs": abs,
        "round": round,
        "pi": math.pi,
        "e": math.e,
    }

    def __init__(self):
        self._history: List[Dict[str, Any]] = []

    def evaluate(self, expression: str) -> Dict[str, Any]:
        """Evaluate a mathematical expression.

        Args:
            expression: Mathematical expression string.

        Returns:
            Result dictionary with value or error.
        """
        try:
            # Parse and evaluate
            result = self._eval_node(ast.parse(expression, mode="eval").body)

            # Record in history
            self._history.append({
                "expression": expression,
                "result": result,
                "success": True,
            })

            return {
                "expression": expression,
                "result": result,
                "success": True,
            }

        except (SyntaxError, ValueError, ZeroDivisionError, TypeError, ArithmeticError) as e:
            error_result = {
                "expression": expression,
                "error": str(e),
                "success": False,
            }

            self._history.append(error_result)
            return error_result

    def _eval_node(self, node: ast.AST) -> Union[int, float]:
        """Recursively evaluate an AST node."""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self.OPS[type(node.op)](left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval_node(node.operand)
            return self.OPS[type(node.op)](operand)
        elif isinstance(node, ast.Call):
            func_name = node.func.id if hasattr(node.func, "id") else str(node.func)
            args = [self._eval_node(arg) for arg in node.args]

            if func_name in self.MATH_FUNCTIONS:
                return self.MATH_FUNCTIONS[func_name](*args)
            else:
                raise ValueError(f"Unknown function: {func_name}")
        elif isinstance(node, ast.Name):
            if node.id in self.MATH_FUNCTIONS:
                return self.MATH_FUNCTIONS[node.id]
            raise ValueError(f"Unknown variable: {node.id}")
        else:
            raise ValueError(f"Unsupported operation: {type(node).__name__}")

    def convert(
        self,
        value: float,
        from_unit: str,
        to_unit: str,
    ) -> Dict[str, Any]:
        """Convert between units.

        Args:
            value: Value to convert.
            from_unit: Source unit.
            to_unit: Target unit.

        Returns:
            Conversion result.
        """
        # Simple length conversions (extend as needed)
        length_factors = {
            ("m", "cm"): 100,
            ("m", "mm"): 1000,
            ("m", "km"): 0.001,
            ("m", "ft"): 3.28084,
            ("m", "in"): 39.3701,
            ("cm", "mm"): 10,
            ("km", "m"): 1000,
        }

        key = (from_unit.lower(), to_unit.lower())
        if key in length_factors:
            result = value * length_factors[key]
            return {
                "value": value,
                "from_unit": from_unit,
                "to_unit": to_unit,
                "result": result,
                "success": True,
            }

        return {
            "value": value,
            "from_unit": from_unit,
            "to_unit": to_unit,
            "error": f"Conversion from {from_unit} to {to_unit} not supported",
            "success": False,
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """Get calculation history."""
        return self._history.copy()

    def clear_history(self) -> None:
        """Clear calculation history."""
        self._history.clear()


# Convenience function for direct use
def calculate(expression: str) -> Dict[str, Any]:
    """Calculate an expression.

    Args:
        expression: Mathematical expression.

    Returns:
        Result dictionary.
    """
    tool = CalculatorTool()
    return tool.evaluate(expression)


# Async wrapper
async def calculator(expression: str) -> Dict[str, Any]:
    """Async calculator function for agents.

    Args:
        expression: Mathematical expression.

    Returns:
        Result dictionary.
    """
    return calculate(expression)
