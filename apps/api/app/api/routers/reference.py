"""Static reference data for the UI: countries, currencies, departments, levels."""

from fastapi import APIRouter
from pydantic import BaseModel

from app.api.deps import CurrentUserDep
from app.domain.money import CURRENCY_EXPONENTS
from app.domain.reference import COUNTRIES, DEPARTMENTS, LEVELS, ROLES, SALARY_CHANGE_REASONS

router = APIRouter(prefix="/reference", tags=["reference"])


class CountryOut(BaseModel):
    code: str
    name: str
    currency_code: str


class CurrencyOut(BaseModel):
    code: str
    exponent: int


class ReferenceOut(BaseModel):
    countries: list[CountryOut]
    currencies: list[CurrencyOut]
    departments: list[str]
    levels: list[str]
    salary_change_reasons: list[str]
    roles: list[str]


@router.get("", response_model=ReferenceOut)
def reference(_user: CurrentUserDep) -> ReferenceOut:
    return ReferenceOut(
        countries=[CountryOut(**c.__dict__) for c in COUNTRIES.values()],
        currencies=[CurrencyOut(code=c, exponent=e) for c, e in CURRENCY_EXPONENTS.items()],
        departments=list(DEPARTMENTS),
        levels=list(LEVELS),
        salary_change_reasons=list(SALARY_CHANGE_REASONS),
        roles=list(ROLES),
    )
