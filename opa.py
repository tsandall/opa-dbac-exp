import requests
import json
from collections import namedtuple


class Decision(object):
    def __init__(self, allow, sql):
        self.allow = allow
        self.sql = sql


def query(input, unknowns, from_table=None):
    response = requests.get('http://localhost:8181/v1/query', params={
        'q': 'data.example.allow=true',
        'unknown': ','.join(['data.' + u for u in unknowns]),
        'input': json.dumps(input),
    })
    body = response.json()
    if 'partial' not in body:
        # Special case for partial result that indicates ALWAYS false.
        return Decision(False, None)
    return Decision(True, translate_to_sql(RegoQuerySet.from_data(body['partial'])))


def translate_to_sql(query_set):

    if len(query_set.queries) == 1 and len(query_set.queries[0].exprs) == 0:
        print "skip"
        # Special case for partial result that indicates ALWAYS true.
        return None

    class unknownCounter(object):
        def __init__(self):
            self.tables = set([])

        def __call__(self, node):
            if isinstance(node, RegoRef):
                self.tables.add(node.operand(1))

    vis = unknownCounter()
    walk_rego(query_set, vis)

    if len(vis.tables) > 1:
        raise ValueError("requires join")

    return SQLWherePredicate(_rego_to_sql_disjunction(query_set))


def _rego_to_sql_disjunction(query_set):
    return SQLDisjunction(*[_rego_to_sql_conjunction(q) for q in query_set.queries])


def _rego_to_sql_conjunction(query):
    return SQLConjunction(*[_rego_to_sql_expr(e) for e in query.exprs])


def _rego_to_sql_expr(expr):
    op = REGO_TO_SQL_OPERATOR_MAP.get(expr.op())
    if isinstance(op, SQLRelationOp):
        return _rego_to_sql_relation_expr(op, expr.operands[0], expr.operands[1])
    raise ValueError('bad operator')


def _rego_to_sql_relation_expr(operator, lhs, rhs):
    if isinstance(lhs.value, RegoRef):
        return SQLRelation(operator, _rego_to_sql_col(lhs.value), SQLConstant(rhs.value.value))
    elif isinstance(rhs.value, RegoRef):
        return SQLRelation(operator, _rego_to_sql_col(rhs.value), SQLConstant(lhs.value.value))
    else:
        raise ValueError("bad relation operands")


def _rego_to_sql_col(ref):
    if len(ref.terms) == 3:
        return SQLColumn(ref.terms[2].value.value, ref.terms[1].value.value)
    raise ValueError("bad column name")


class SQLJoinPredicate(object):
    INNER = 'INNER JOIN'

    def __init__(self, type, tables, expr):
        self.type = type
        self.tables = tables
        self.expr = expr

    def sql(self, include_join=False):
        s = ''
        if include_join:
            s = ' '.join([self.type + ' ' + t for t in self.tables]) + ' ON '
        return s + s.expr.sql()


class SQLWherePredicate(object):
    def __init__(self, expr):
        self.expr = expr

    def sql(self):
        return self.expr.sql()


class SQLDisjunction(object):
    def __init__(self, *conjunction):
        self.conjunction = conjunction

    def sql(self):
        return '(' + " OR ".join([c.sql() for c in self.conjunction]) + ')'


class SQLConjunction(object):
    def __init__(self, *relation):
        self.relation = relation

    def sql(self):
        if len(self.relation) == 0:
            return '1'
        return '(' + " AND ".join([r.sql() for r in self.relation]) + ')'


class SQLRelation(object):
    def __init__(self, operator, lhs, rhs):
        self.operator = operator
        self.lhs = lhs
        self.rhs = rhs

    def sql(self):
        return "%s %s %s" % (self.lhs.sql(), self.operator.sql(), self.rhs.sql())


class SQLColumn(object):
    def __init__(self, name, table=''):
        self.table = table
        self.name = name

    def sql(self):
        if self.table:
            return "%s.%s" % (self.table, self.name)
        return str(self.name)


class SQLConstant(object):
    def __init__(self, value):
        self.value = value

    def sql(self):
        return json.dumps(self.value)


class SQLRelationOp(object):
    def __init__(self, value):
        self.value = value

    def sql(self):
        return self.value


REGO_TO_SQL_OPERATOR_MAP = {
    'eq': SQLRelationOp('='),
}


def walk_sql(node, vis):
    next = vis(node)
    if next is None:
        return
    if isinstance(node, SQLWherePredicate):
        walk_sql(node.expr, next)
    elif isinstance(node, SQLJoinPredicate):
        walk_sql(node.expr, next)
    elif isinstance(node, SQLDisjunction):
        for child in node.conjunction:
            walk_sql(child, next)
    elif isinstance(node, SQLConjunction):
        for child in node.relation:
            walk_sql(child, next)
    elif isinstance(node, SQLRelation):
        walk_sql(node.operator, next)
        walk_sql(node.lhs, next)
        walk_sql(node.rhs, next)


def pp_sql(node):
    class printer(object):
        def __init__(self, indent):
            self.indent = indent

        def __call__(self, node):
            print ' ' * self.indent, node.__class__.__name__
            return printer(self.indent+2)

    vis = printer(0)
    walk_sql(node, vis)


class RegoQuerySet(object):
    def __init__(self, *queries):
        self.queries = queries

    @classmethod
    def from_data(cls, data):
        return cls(*[RegoQuery.from_data(q) for q in data])


class RegoQuery(object):
    def __init__(self, *exprs):
        self.exprs = exprs

    @classmethod
    def from_data(cls, data):
        return cls(*[RegoExpr.from_data(e) for e in data])


class RegoQuery(object):
    def __init__(self, *exprs):
        self.exprs = exprs

    @classmethod
    def from_data(cls, data):
        return cls(*[RegoExpr.from_data(e) for e in data])


class RegoExpr(object):
    def __init__(self, operator, *operands):
        self.operator = operator
        self.operands = operands

    def op(self):
        return ".".join([str(t.value.value) for t in self.operator.value.terms])

    @classmethod
    def from_data(cls, data):
        terms = data["terms"]
        return cls(RegoTerm.from_data(terms[0]), *[RegoTerm.from_data(t) for t in terms[1:]])


class RegoTerm(object):
    def __init__(self, value):
        self.value = value

    @classmethod
    def from_data(cls, data):
        return cls(REGO_VALUE_MAP[data["type"]].from_data(data["value"]))


class RegoScalar(object):
    def __init__(self, value):
        self.value = value

    @classmethod
    def from_data(cls, data):
        return cls(data)


class RegoVar(object):
    def __init__(self, value):
        self.value = value

    @classmethod
    def from_data(cls, data):
        return cls(data)


class RegoRef(object):
    def __init__(self, *terms):
        self.terms = terms

    @classmethod
    def from_data(cls, data):
        return cls(*[RegoTerm.from_data(x) for x in data])


class RegoArray(object):
    def __init__(self, *terms):
        self.terms = terms

    @classmethod
    def from_data(cls, data):
        return cls(*[RegoTerm.from_data(x) for x in data])


class RegoSet(object):
    def __init__(self, *terms):
        self.terms = terms

    @classmethod
    def from_data(cls, data):
        return cls(*[RegoTerm.from_data(x) for x in data])


class RegoObject(object):
    def __init__(self, *pairs):
        self.pairs = pairs

    @classmethod
    def from_method(cls, data):
        return cls(*[(RegoTerm.from_data(p[0]), RegoTerm.from_data(p[1])) for p in data])


REGO_VALUE_MAP = {
    "null": RegoScalar,
    "boolean": RegoScalar,
    "number": RegoScalar,
    "string": RegoScalar,
    "var": RegoVar,
    "ref": RegoRef,
    "array": RegoArray,
    "set": RegoSet,
    "object": RegoObject,
}


def walk_rego(node, vis):
    next = vis(node)
    if next is None:
        return

    if isinstance(node, RegoQuerySet):
        for q in node.queries:
            walk_rego(q, next)
    elif isinstance(node, RegoQuery):
        for e in node.exprs:
            walk_rego(e, next)
    elif isinstance(node, RegoExpr):
        walk_rego(node.operator, next)
        for o in node.operands:
            walk_rego(o, next)
    elif isinstance(node, RegoTerm):
        walk_rego(node.value, next)
    elif isinstance(node, (RegoRef, RegoArray, RegoSet)):
        for t in node.terms:
            walk_rego(t, next)
    elif isinstance(node, RegoObject):
        for p in node.pairs:
            walk_rego(p[0], next)
            walk_rego(p[1], next)


def pp_rego(node):
    class printer(object):
        def __init__(self, indent):
            self.indent = indent

        def __call__(self, node):
            print ' ' * self.indent, node.__class__.__name__
            return printer(self.indent+2)

    vis = printer(0)
    walk_rego(node, vis)
