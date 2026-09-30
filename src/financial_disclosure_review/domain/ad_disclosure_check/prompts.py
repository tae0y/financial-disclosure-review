"""The task text of the disclosure judgment call."""

DISCLOSURE_ORIGINAL_TASK = """당신은 카드회사 광고 페이지 원문(text)에 광고 의무표시 기준(items)이 요구하는 내용이
들어 있는지 판단합니다. items의 각 항목은 code, criterion(기준 문장), applies_condition(이 기준이
적용되는 조건, 없으면 null)으로 구성됩니다. 각 항목마다 다음 순서로 답합니다.

1. applies_condition이 null이면 condition_status는 해당없음으로 둡니다. applies_condition이 있으면
   text의 내용만으로 그 조건이 실제로 성립하는지 판단합니다.
   - 성립: 조건이 성립함을 text에서 확인할 수 있음
   - 불성립: 조건이 성립하지 않음을 text에서 확인할 수 있음
   - 불명확: text만으로는 조건 성립 여부를 알 수 없음. 성립 또는 불성립으로 추측하지 않습니다.
2. condition_status가 성립 또는 해당없음일 때만 criterion을 text 기준으로 판단해 verdict를
   정합니다(적합/부적합/판정 불가). criterion이 요구하는 내용이 text에 있으면 적합, 없거나 기준에
   못 미치면 부적합입니다. condition_status가 불성립 또는 불명확이면 verdict는 반드시 판정 불가,
   quote는 반드시 빈 문자열입니다.
3. verdict가 적합이면 quote에 그 판단을 뒷받침하는 text의 문장을 그대로 인용합니다(요약·수정 금지).
   부적합이나 판정 불가는 인용할 문장이 없으면 quote를 빈 문자열로 둡니다.
4. reason에는 조건 판단과 criterion 판단의 결론과 짧은 근거만 씁니다. 내부 추론 과정을 나열하지
   않습니다.

text에 없는 내용을 있다고 답하지 않습니다. 확실하지 않으면 판정 불가로 답합니다."""
