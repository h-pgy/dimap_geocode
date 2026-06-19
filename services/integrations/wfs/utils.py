from .models import CqlFilter, CqlPredicate

CqlValue = str | int | float | bool


def cql_eq(field: str, value: CqlValue) -> CqlFilter:
    return CqlFilter(predicates=[CqlPredicate(field=field, op="=", value=value)])


def cql_not_eq(field: str, value: CqlValue) -> CqlFilter:
    return CqlFilter(predicates=[CqlPredicate(field=field, op="<>", value=value)])


def cql_gt(field: str, value: CqlValue) -> CqlFilter:
    return CqlFilter(predicates=[CqlPredicate(field=field, op=">", value=value)])


def cql_lt(field: str, value: CqlValue) -> CqlFilter:
    return CqlFilter(predicates=[CqlPredicate(field=field, op="<", value=value)])


def cql_gte(field: str, value: CqlValue) -> CqlFilter:
    return CqlFilter(predicates=[CqlPredicate(field=field, op=">=", value=value)])


def cql_lte(field: str, value: CqlValue) -> CqlFilter:
    return CqlFilter(predicates=[CqlPredicate(field=field, op="<=", value=value)])


def cql_like(field: str, value: str) -> CqlFilter:
    return CqlFilter(predicates=[CqlPredicate(field=field, op="LIKE", value=value)])


def cql_ilike(field: str, value: str) -> CqlFilter:
    return CqlFilter(predicates=[CqlPredicate(field=field, op="ILIKE", value=value)])
