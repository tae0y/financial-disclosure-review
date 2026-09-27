"""Answer shapes of the three-step classification, and the page type each product type implies."""

from typing import Literal

from pydantic import BaseModel

PAGE_TYPE_BY_PRODUCT = {
    "신용카드": "상품광고",
    "장기카드대출": "상품광고",
    "할부금융·리스": "상품광고",
    "단기카드대출": "업무광고",
    "리볼빙": "업무광고",
}


class ClassifyAnswer(BaseModel):
    single_product_quote: str
    single_product_reason: str
    single_product: bool
    loan_product_quote: str | None
    loan_product_reason: str | None
    loan_product: bool | None
    evidence: str | None
    product_type_reason: str | None
    product_type: (
        Literal["신용카드", "장기카드대출", "단기카드대출", "리볼빙", "할부금융·리스"] | None
    )
    page_subject: str
    confidence: Literal["high", "medium", "low"]


class VerifyAnswer(BaseModel):
    reason: str
    answer: Literal["예", "아니오"]
