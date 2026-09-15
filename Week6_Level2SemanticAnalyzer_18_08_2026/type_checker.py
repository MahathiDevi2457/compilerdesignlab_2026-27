"""
Semantic/type checker for Week 6 TinyCStr.

The checker walks each function AST using that function's local symbol table.
Each check_* method returns (possibly_rewritten_node, resulting_type).
Whenever a legal implicit numeric conversion is needed, a Cast node is
inserted into the returned AST.
"""

from ast_nodes import Const, Var, Assign, Print, BinOp, RelOp, Cast, Ternary
from SymbolTable import DataType
from type_rules import is_numeric, promote, SemanticError


class TypeChecker:
    def __init__(self, symbol_table):
        self.symbol_table = symbol_table
        self.errors = []

    def error(self, message, lineno=None):
        """Record an error and continue checking the rest of the program."""
        self.errors.append(SemanticError(message, lineno))

    @staticmethod
    def _type_name(datatype):
        return datatype.name if datatype is not None else "UNKNOWN"

    @staticmethod
    def _cast_if_needed(node, from_type, to_type, lineno=None):
        """Insert an explicit Cast only when the two types differ."""
        if from_type == to_type:
            return node
        return Cast(to_type, node, lineno=lineno)

    def check_expr(self, node):
        """Dispatch expression nodes to the appropriate checker."""
        if isinstance(node, Const):
            return node, node.type
        if isinstance(node, Var):
            return self.check_var(node)
        if isinstance(node, BinOp):
            return self.check_binop(node)
        if isinstance(node, RelOp):
            return self.check_relop(node)
        if isinstance(node, Cast):
            return self.check_cast(node)
        if isinstance(node, Ternary):
            return self.check_ternary(node)

        self.error(f"unknown expression node {type(node).__name__}",
                   getattr(node, "lineno", None))
        return node, DataType.INT

    def check_var(self, node):
        """
        Check that a variable has been declared.

        On an undeclared variable, report an error and return INT as a
        recovery type so checking can continue.
        """
        entry = self.symbol_table.getSymbol(node.name)
        if entry is None:
            self.error(f"undeclared variable '{node.name}'", node.lineno)
            return node, DataType.INT
        return node, entry.getDataType()

    def check_binop(self, node):
        """
        Check +, -, *, /.

        Both operands must be numeric. Numeric operands are promoted using
        type_rules.promote(), and Cast nodes are inserted where required.
        """
        left, left_type = self.check_expr(node.left)
        right, right_type = self.check_expr(node.right)

        if not is_numeric(left_type) or not is_numeric(right_type):
            self.error(
                f"operator '{node.op}' requires numeric operands, got "
                f"{self._type_name(left_type)} and {self._type_name(right_type)}",
                node.lineno,
            )
            return BinOp(node.op, left, right, lineno=node.lineno), DataType.INT

        result_type = promote(left_type, right_type)
        left = self._cast_if_needed(left, left_type, result_type,
                                    getattr(left, "lineno", node.lineno))
        right = self._cast_if_needed(right, right_type, result_type,
                                     getattr(right, "lineno", node.lineno))

        return BinOp(node.op, left, right, lineno=node.lineno), result_type

    def check_relop(self, node):
        """
        Check <, >, <=, >=, ==, !=.

        TinyCStr relational operands must be numeric. Mixed numeric operands
        are promoted to a common type. A relational expression has type INT
        (0/1), matching the language's C-like convention.
        """
        left, left_type = self.check_expr(node.left)
        right, right_type = self.check_expr(node.right)

        if not is_numeric(left_type) or not is_numeric(right_type):
            self.error(
                f"operator '{node.op}' requires comparable numeric operands, got "
                f"{self._type_name(left_type)} and {self._type_name(right_type)}",
                node.lineno,
            )
            return RelOp(node.op, left, right, lineno=node.lineno), DataType.INT

        common_type = promote(left_type, right_type)
        left = self._cast_if_needed(left, left_type, common_type,
                                    getattr(left, "lineno", node.lineno))
        right = self._cast_if_needed(right, right_type, common_type,
                                     getattr(right, "lineno", node.lineno))

        return RelOp(node.op, left, right, lineno=node.lineno), DataType.INT

    def check_ternary(self, node):
        """
        Check cond ? then_expr : else_expr.

        The condition must be numeric. Equal branch types are accepted as-is.
        Two different numeric branch types are promoted to a common type and
        the needed Cast node(s) are inserted. STRING can only unify with
        STRING; STRING mixed with a numeric type is an error.
        """
        cond, cond_type = self.check_expr(node.cond)
        then_expr, then_type = self.check_expr(node.then_expr)
        else_expr, else_type = self.check_expr(node.else_expr)

        if not is_numeric(cond_type):
            self.error(
                f"ternary condition must be numeric, got {self._type_name(cond_type)}",
                getattr(node.cond, "lineno", node.lineno),
            )

        if then_type == else_type:
            result_type = then_type
        elif is_numeric(then_type) and is_numeric(else_type):
            result_type = promote(then_type, else_type)
            then_expr = self._cast_if_needed(
                then_expr, then_type, result_type,
                getattr(then_expr, "lineno", node.lineno))
            else_expr = self._cast_if_needed(
                else_expr, else_type, result_type,
                getattr(else_expr, "lineno", node.lineno))
        else:
            self.error(
                f"incompatible ternary branch types "
                f"{self._type_name(then_type)} and {self._type_name(else_type)}",
                node.lineno,
            )
            # Recovery: preserve a useful intended type and continue.
            result_type = then_type

        return Ternary(cond, then_expr, else_expr, lineno=node.lineno), result_type

    def check_cast(self, node):
        """
        Check an explicit cast.

        TinyCStr permits casts among numeric types only. The result type is
        always the cast's target type, even after an invalid cast is reported;
        this is the error-recovery policy documented for Week 6.
        """
        expr, source_type = self.check_expr(node.expr)
        target_type = node.target_type

        if not (is_numeric(source_type) and is_numeric(target_type)):
            self.error(
                f"invalid cast from {self._type_name(source_type)} "
                f"to {self._type_name(target_type)}",
                node.lineno,
            )

        return Cast(target_type, expr, lineno=node.lineno), target_type

    def check_assign_stmt(self, node):
        """
        Check assignment target declaration and assignment conversion rules.

        Assignment is legal when both sides have the same type or both are
        numeric. For different numeric types, make the conversion explicit by
        inserting Cast(target_type, expr). STRING is assignable only to STRING.
        """
        var, var_type = self.check_var(node.var)
        expr, expr_type = self.check_expr(node.expr)

        if var_type == expr_type:
            pass
        elif is_numeric(var_type) and is_numeric(expr_type):
            expr = Cast(var_type, expr,
                        lineno=getattr(expr, "lineno", node.lineno))
        else:
            self.error(
                f"cannot assign {self._type_name(expr_type)} "
                f"to {self._type_name(var_type)} variable '{node.var.name}'",
                node.lineno,
            )

        return Assign(var, expr, lineno=node.lineno), var_type

    def check_print_stmt(self, node):
        """Type-check the expression being printed."""
        expr, expr_type = self.check_expr(node.expr)
        return Print(expr, lineno=node.lineno), expr_type

    def check_stmt(self, node):
        """Dispatch a statement node."""
        if isinstance(node, Assign):
            return self.check_assign_stmt(node)
        if isinstance(node, Print):
            return self.check_print_stmt(node)

        self.error(f"unknown statement node {type(node).__name__}",
                   getattr(node, "lineno", None))
        return node, DataType.INT

    def check_function(self, function):
        """Type-check and rewrite all statements in one function."""
        checked_statements = []
        for stmt in function.getStatementsAstList():
            checked_stmt, _ = self.check_stmt(stmt)
            checked_statements.append(checked_stmt)
        function.setStatementsAstList(checked_statements)
        return self.errors


def check_program(program):
    """
    Type-check every function in a Program and return one combined error list.

    Each function uses its own local symbol table, so a fresh TypeChecker is
    created for each function.
    """
    errors = []
    for function in program.getFunctions():
        checker = TypeChecker(function.getLocalSymbolTable())
        checker.check_function(function)
        errors.extend(checker.errors)
    return errors

