"""
Affordability engine.

Calculates whether a lead can afford a property based on:
- Income (monthly or annual)
- Budget range
- Property price
- Buy vs. rent scenario

Simple rules-based engine to be expanded with more sophisticated logic.
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def calculate_affordability(
    income: float,
    property_price: float,
    buy_or_rent: str,
    deposit_percent: float = 20.0,
    interest_rate: float = 0.05,
    loan_term_years: int = 25,
) -> dict:
    """
    Calculate affordability metrics for a lead.

    Args:
        income: Annual income (gross).
        property_price: Total property price.
        buy_or_rent: 'buy' or 'rent'.
        deposit_percent: Deposit as % of property price (for buy scenarios).
        interest_rate: Annual interest rate (for buy scenarios).
        loan_term_years: Mortgage term in years.

    Returns:
        Dict with 'affordable' bool, 'ratio' float, 'max_price' float, and 'message'.
    """
    result = {
        "affordable": False,
        "ratio": 0.0,
        "max_price": 0.0,
        "message": "",
    }

    if buy_or_rent == "buy":
        # Rough mortgage calculation: max loan 4.5x annual income
        max_loan = income * 4.5
        deposit = property_price * (deposit_percent / 100)
        max_price = max_loan + deposit

        result["max_price"] = round(max_price, 2)
        result["ratio"] = round(property_price / income, 2) if income > 0 else 0

        if property_price <= max_price:
            result["affordable"] = True
            result["message"] = (
                f"Based on an estimated income of ${income:,.0f}/year, "
                f"a property up to ${max_price:,.0f} is within reach "
                f"(with a {deposit_percent:.0f}% deposit)."
            )
        else:
            result["message"] = (
                f"This property (${property_price:,.0f}) exceeds the estimated "
                f"maximum affordable price of ${max_price:,.0f}."
            )
    elif buy_or_rent == "rent":
        # Rule: monthly rent should be ≤ 30% of monthly income
        monthly_income = income / 12
        max_monthly_rent = monthly_income * 0.30
        result["max_price"] = round(max_monthly_rent, 2)
        result["ratio"] = round(property_price / monthly_income, 2) if monthly_income > 0 else 0

        if property_price <= max_monthly_rent:
            result["affordable"] = True
            result["message"] = (
                f"With a monthly income of ${monthly_income:,.0f}, "
                f"a rent of up to ${max_monthly_rent:,.0f}/month is affordable."
            )
        else:
            result["message"] = (
                f"This rent (${property_price:,.0f}/month) exceeds the recommended "
                f"30%% threshold of ${max_monthly_rent:,.0f}/month."
            )

    logger.debug(
        "Affordability: buy_or_rent=%s, income=%s, price=%s -> %s",
        buy_or_rent,
        income,
        property_price,
        result["affordable"],
    )
    return result