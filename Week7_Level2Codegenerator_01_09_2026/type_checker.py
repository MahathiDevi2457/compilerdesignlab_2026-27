"""
TinyCStr Level 2 -- Semantic Analysis / Type Checker.

FULLY IMPLEMENTED this week -- this is Week 6's exercise, now carried
forward as infrastructure for Week 7's codegen.

WEEK 7 ADDITION (flagged, small): check_expr() now also stamps
`node.result_type` on whatever node it returns, for EVERY expression
node -- Const, Var, BinOp, RelOp, Cast, Ternary alike. This didn't
matter for Week 6 (which only needed the RETURNED type, to
keep checking the rest of the tree) but Week 7's tac_generator.py needs
to know each node's resolved type when it walks the AST a second time
to emit typed 3AC, without re-running type inference from scratch.
Reading `node.result_type` directly is that lookup.
"""
from ast_nodes import Const, Var, Assign, Print, BinOp, RelOp, Cast, Ternary
from SymbolTable import DataType
from type_rules import is_numeric, promote, SemanticError


class TypeChecker:
    def __init__(self):
        self.errors = []

    def error(self, message, lineno):
        self.errors.append(SemanticError(message, lineno))

    def check_function(self, function):
        self.symbol_table = function.getLocalSymbolTable()
        checked_stmts = []
        for stmt in function.getStatementsAstList():
            checked_stmts.append(self.check_stmt(stmt))
        function.setStatementsAstList(checked_stmts)
        return self.errors

    def check_stmt(self, stmt):
        if isinstance(stmt, Assign):
            return self.check_assign_stmt(stmt)
        elif isinstance(stmt, Print):
            return self.check_print_stmt(stmt)
        else:
            raise ValueError(f"unexpected statement type: {type(stmt)}")

    def check_expr(self, node):
        if isinstance(node, Const):
            result_node, result_type = node, node.type
        elif isinstance(node, Var):
            result_node, result_type = self.check_var(node)
        elif isinstance(node, BinOp):
            result_node, result_type = self.check_binop(node)
        elif isinstance(node, RelOp):
            result_node, result_type = self.check_relop(node)
        elif isinstance(node, Cast):
            result_node, result_type = self.check_cast(node)
        elif isinstance(node, Ternary):
            result_node, result_type = self.check_ternary(node)
        else:
            raise ValueError(f"unexpected expr node type: {type(node)}")
        result_node.result_type = result_type  # WEEK 7 addition
        return result_node, result_type

    def check_var(self, node):
        entry = self.symbol_table.getSymbol(node.name)
        if entry is None:
            self.error(f"undeclared variable '{node.name}'", node.lineno)
            return node, DataType.INT
        return node, entry.getDataType()

    def _maybe_cast(self, child, child_type, target_type, lineno):
        if child_type != target_type:
            return Cast(target_type, child, lineno=lineno)
        return child

    def check_binop(self, node):
        left, left_type = self.check_expr(node.left)
        right, right_type = self.check_expr(node.right)
        if not is_numeric(left_type) or not is_numeric(right_type):
            self.error(f"arithmetic operator '{node.op}' not supported for type "
                       f"{left_type if not is_numeric(left_type) else right_type}", node.lineno)
            node.left, node.right = left, right
            return node, DataType.INT
        result_type = promote(left_type, right_type)
        node.left = self._maybe_cast(left, left_type, result_type, node.lineno)
        node.right = self._maybe_cast(right, right_type, result_type, node.lineno)
        return node, result_type

    def check_relop(self, node):
        left, left_type = self.check_expr(node.left)
        right, right_type = self.check_expr(node.right)
        if is_numeric(left_type) and is_numeric(right_type):
            result_type = promote(left_type, right_type)
            node.left = self._maybe_cast(left, left_type, result_type, node.lineno)
            node.right = self._maybe_cast(right, right_type, result_type, node.lineno)
        elif left_type == DataType.STRING and right_type == DataType.STRING:
            node.left, node.right = left, right
        else:
            self.error(f"cannot compare {left_type} and {right_type}", node.lineno)
            node.left, node.right = left, right
        return node, DataType.INT

    def check_cast(self, node):
        expr, expr_type = self.check_expr(node.expr)
        if not is_numeric(expr_type):
            self.error(f"cannot cast {expr_type} to {node.target_type}", node.lineno)
        node.expr = expr
        return node, node.target_type

    def check_ternary(self, node):
        cond, cond_type = self.check_expr(node.cond)
        then_e, then_type = self.check_expr(node.then_expr)
        else_e, else_type = self.check_expr(node.else_expr)

        if not is_numeric(cond_type):
            self.error(f"ternary condition must be numeric, got {cond_type}", node.lineno)

        if then_type == else_type:
            result_type = then_type
        elif is_numeric(then_type) and is_numeric(else_type):
            result_type = promote(then_type, else_type)
            then_e = self._maybe_cast(then_e, then_type, result_type, node.lineno)
            else_e = self._maybe_cast(else_e, else_type, result_type, node.lineno)
        else:
            self.error(f"ternary branches have incompatible types: {then_type} and {else_type}",
                       node.lineno)
            result_type = then_type

        node.cond, node.then_expr, node.else_expr = cond, then_e, else_e
        return node, result_type

    def check_assign_stmt(self, stmt):
        entry = self.symbol_table.getSymbol(stmt.var.name)
        if entry is None:
            self.error(f"undeclared variable '{stmt.var.name}'", stmt.var.lineno)
            expr, expr_type = self.check_expr(stmt.expr)
            stmt.expr = expr
            return stmt

        var_type = entry.getDataType()
        expr, expr_type = self.check_expr(stmt.expr)
        if var_type != expr_type:
            if is_numeric(var_type) and is_numeric(expr_type):
                expr = Cast(var_type, expr, lineno=stmt.lineno)
                expr.result_type = var_type
            else:
                self.error(f"cannot assign {expr_type} to variable '{stmt.var.name}' of type "
                           f"{var_type}", stmt.lineno)
        stmt.expr = expr
        return stmt

    def check_print_stmt(self, stmt):
        expr, expr_type = self.check_expr(stmt.expr)
        stmt.expr = expr
        return stmt


def check_program(program):
    all_errors = []
    for function in program.getFunctions():
        checker = TypeChecker()
        errors = checker.check_function(function)
        all_errors.extend(errors)
    return all_errors
