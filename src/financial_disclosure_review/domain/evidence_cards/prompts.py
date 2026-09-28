"""The task text of the evidence-card extraction call."""

EVIDENCE_CARD_TASK = """당신은 카드회사 상품 페이지의 원문에서 사실 단위의 증거 카드를 뽑습니다.
sources는 원문을 줄 단위로 나눈 목록입니다. 각 줄에는 source_id(dom-N)와 text(원문 그대로)가
있습니다. product_type은 이 페이지가 소개하는 상품 유형입니다.

[절대 금지]
- 법적 판정(적합/부적합, 위반 여부)을 내리지 않습니다. 사실만 뽑습니다.
- quote에 없는 문장·수치·조건을 새로 만들지 않습니다.
- quote는 sources 중 하나의 text에서 그대로(끊어 붙이지 않고) 옮겨 적습니다. 요약하거나
  문장을 고치지 않습니다.
- qualifiers, exceptions, numbers의 각 항목은 quote 안에 실제로 나오는 글자 그대로의
  부분 문자열이어야 합니다. numbers는 원문에 쓰인 글자 그대로("30만원", "5%")의 문자열입니다.
  숫자로 바꾸거나 단위를 떼지 않습니다.

[카드 종류(kind)]
benefit_claim(혜택), rate_claim(금리), fee_claim(수수료·연회비), eligibility(자격), condition(조건),
exception(예외·제외 대상), warning(경고·불이익), footnote(각주·부기) 중 하나를 고릅니다.

[답변 항목]
각 카드는 kind, subject(무엇에 대한 카드인지 짧게), claim(핵심 주장·사실 한 문장),
qualifiers(그 claim에 붙는 조건들, quote 안의 문구 그대로), exceptions(제외·예외 대상,
quote 안의 문구 그대로), numbers(quote 안에 있는 수치 문자열들), quote(원문 인용),
source_id(그 quote가 나온 줄의 id)를 답합니다.

조건·예외·수치가 없는 카드는 qualifiers, exceptions, numbers를 빈 목록으로 둡니다.
같은 내용을 두 번 뽑지 않습니다. previous_problems가 있으면 그 문제를 고쳐 다시 답합니다."""
