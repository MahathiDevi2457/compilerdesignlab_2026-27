"""
TinyCStr -- AST to Three-Address Code (triple form) generator.

Read docs/typed_3ac_reference.md before editing this file.

Your work this week is entirely in the "LEVEL 2" section: RelOp, Cast,
and Ternary each need a new gen_expr() case, staged the same way earlier
weeks staged new grammar/lexer rules.
"""
from SymbolTable import DataType
from ast_nodes import Const, Var, Assign, Print, BinOp, RelOp, Cast, Ternary
from three_address_code import (
    TripleTAC, BinOpTriple, AssignTriple, PrintTriple,
    RelOpTriple, CastTriple, SelectTriple,
)


class TACGenerator:
    def __init__(self):
        self.program = TripleTAC()

    def generate(self, function):
        """
        Provided -- the entry point. Walks function.getStatementsAstList()
        in order and returns the finished TripleTAC.
        """
        for stmt in function.getStatementsAstList():
            self.gen_stmt(stmt)
        return self.program

    # ------------------------------------------------------------------
    # LEVEL 1 -- unchanged, do not modify
    # ------------------------------------------------------------------
    def gen_stmt(self, stmt):
        if isinstance(stmt, Assign):
            operand = self.gen_expr(stmt.expr)
            self.program.append(AssignTriple(stmt.var.name, operand))
        elif isinstance(stmt, Print):
            operand = self.gen_expr(stmt.expr)
            self.program.append(PrintTriple(operand))
        else:
            raise ValueError(f"unexpected statement type: {type(stmt)}")

    def gen_expr(self, node):
        """
        NOTE on Const: string/char literal VALUES are just plain text
        ("hello", "x"), indistinguishable by inspection from a variable
        name -- unlike an int/double literal, which is self-evidently
        numeric by its shape. To keep that distinction visible all the
        way down to tac_to_mips.py's literal_kind() (see
        docs/typed_3ac_reference.md), string/char Const operands are
        wrapped in their ORIGINAL quote characters here.
        """
        if isinstance(node, Const):
            if node.type == DataType.STRING:
                return f'"{node.value}"'
            elif node.type == DataType.CHAR:
                return f"'{node.value}'"
            else:
                return str(node.value)
        elif isinstance(node, Var):
            return node.name
        elif isinstance(node, BinOp):
            left = self.gen_expr(node.left)
            right = self.gen_expr(node.right)
            return self.program.append(BinOpTriple(node.op, left, right, node.result_type))
        # ------------------------------------------------------------------
        # LEVEL 2 -- this week's TODOs
        # ------------------------------------------------------------------
        elif isinstance(node, RelOp):
            return self.gen_relop(node)
        elif isinstance(node, Cast):
            return self.gen_cast(node)
        elif isinstance(node, Ternary):
            return self.gen_ternary(node)
        else:
            raise ValueError(f"unexpected expr node type: {type(node)}")

    def gen_relop(self, node):
        """
        TODO(week-7): mirror the BinOp case exactly, but build a
        RelOpTriple instead of a BinOpTriple:

            left = self.gen_expr(node.left)
            right = self.gen_expr(node.right)
            return self.program.append(RelOpTriple(node.op, left, right, node.left.result_type))

        Note the type passed is node.left.result_type (the OPERANDS'
        promoted type -- Week 6 already made node.left/node.right the
        same type via inserted Casts, so either child's result_type
        works identically), NOT node.result_type (which is always
        DataType.INT for a RelOp -- that's the comparison's own logical
        result, not what MIPS instruction family to use for the
        comparison itself). See docs/typed_3ac_reference.md if this
        distinction isn't clear.
        """
        raise NotImplementedError("implement TACGenerator.gen_relop()")

    def gen_cast(self, node):
        """
        TODO(week-7): build a CastTriple. You need BOTH the source type
        (node.expr.result_type -- the type of whatever's being
        converted) and the target type (node.target_type, already on
        the Cast AST node since Week 5):

            arg = self.gen_expr(node.expr)
            return self.program.append(
                CastTriple(node.expr.result_type, node.target_type, arg))
        """
        raise NotImplementedError("implement TACGenerator.gen_cast()")

    def gen_ternary(self, node):
        """
        TODO(week-7): resolve all three subexpressions (cond, then_expr,
        else_expr) via gen_expr(), then build ONE SelectTriple -- do NOT
        emit any branch/label triples here, that happens only in
        tac_to_mips.py (see three_address_code.py's module docstring for
        why):

            cond = self.gen_expr(node.cond)
            then_val = self.gen_expr(node.then_expr)
            else_val = self.gen_expr(node.else_expr)
            return self.program.append(
                SelectTriple(cond, node.cond.result_type, then_val, else_val,
                             node.result_type))
        """
        raise NotImplementedError("implement TACGenerator.gen_ternary()")


def generate_for_function(function):
    """Convenience wrapper: generate() a fresh TACGenerator for one function."""
    return TACGenerator().generate(function)
