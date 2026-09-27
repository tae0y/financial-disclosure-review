"""The labelling, verdict and vision prompts, kept verbatim."""

LABEL_TASK = """당신은 카드회사 상품 페이지의 글자 표시 방식을 점검하는 검토자를 돕습니다.
blocks는 페이지에서 측정한 글자 블록입니다. 한 줄이 블록 하나이며 형식은 columns와 같습니다.
flags의 H는 캡처한 모든 화면에서 숨겨져 있던 블록입니다.
mandatory_items는 이 페이지에 반드시 표시해야 하는 의무표시 항목의 기준 문장입니다.
images는 페이지 본문에 있는 이미지의 id와 대체 텍스트입니다. 이미지 속 글자는 측정할 수 없습니다.

각 블록이 아래 묶음 중 어디에 속하는지 id로만 답합니다. 한 블록이 여러 묶음에 속할 수 있습니다.
- mandatory: mandatory_items 중 어느 항목이든 그 내용을 전하는 문구 (이자율, 수수료, 연체, 심의필, 유의사항, 상품설명서 권유 등)
- warnings: 신용평점 하락, 연체 시 불이익, 원리금 상환 의무처럼 소비자에게 경고하는 문구
- rates: 이자율·수수료율(연체이자율 포함)을 나타내는 문구
- benefits: 소비자가 얻는 혜택(할인, 적립, 무이자, 면제 등)을 알리는 문구
- penalties: 소비자가 부담하거나 혜택이 제한되는 내용(연회비, 수수료, 연체, 한도, 조건 제한)을 알리는 문구
- image_disclosure: images 중 대체 텍스트(alt)가 의무표시·경고·이자율·수수료 같은 안내 글자를 직접 언급하는 이미지.
  id와, 그 근거가 되는 alt 안의 구절(alt_phrase, alt에 있는 그대로 3글자 이상)을 함께 답합니다.
  alt가 비어 있거나, 상품명·카드 앞면·슬라이드 번호처럼 안내 글자와 무관한 설명이면 넣지 않습니다.
  넣는 예: alt가 "연체이자율 안내"인 경우. 넣지 않는 예: alt가 "OO카드 앞면"인 경우.

규칙
1. blocks와 images에 없는 id를 쓰지 않습니다.
2. 글자 내용만으로 판단합니다. 특정 회사나 사이트에 대해 미리 알고 있는 내용을 쓰지 않습니다.
3. 확실하지 않은 블록은 넣지 않습니다.
4. note에는 라벨링 중 판단이 어려웠던 점을 한두 문장으로 씁니다. 없으면 빈 문자열입니다."""

VERDICT_TASK = """당신은 카드회사 상품 페이지의 표시방법을 점검합니다.
items의 각 항목은 code, criterion(점검 기준), measures(코드가 측정한 값), blocks(관련 블록)로 이루어집니다.
blocks 한 줄의 형식은 columns와 같고, flags의 H는 캡처한 모든 화면에서 숨겨져 있던 블록,
D는 처음에는 숨겨져 있다가 사용자 조작으로 나타난 블록, M은 문장 앞에 기호가 있는 블록,
O는 블록이 한 줄을 혼자 차지함, S는 그 줄에 든 문장 수입니다.
assumptions는 코드가 적용한 해석이므로 그대로 따릅니다. measures가 비어 있는 항목은 blocks의 글자가 근거입니다.
previous_problems가 있으면 앞선 답의 문제이므로 고쳐서 다시 답합니다.

규칙
1. verdict는 항상 "적합"이면 광고가 기준을 지킨 것, "부적합"이면 기준을 어긴 것입니다.
   criterion이 "~했는가?"처럼 위반 여부를 묻는 문장이어도 이 뜻은 바뀌지 않습니다.
2. 근거는 measures와 blocks의 글자·값뿐입니다. 숫자를 새로 계산하거나 지어내지 않습니다.
3. 근거가 부족하거나 측정할 수 없으면 "판정 불가"로 답하고 reason에 무엇이 없는지 씁니다.
   H 블록은 어떤 캡처 화면에서도 보이지 않았으므로 사용자가 볼 수 있었는지 알 수 없습니다.
   "숨겼다"는 판정의 근거는 D 블록(사용자 조작으로 나타난 블록)이어야 하고, 근거가 H 블록뿐이면 "판정 불가"입니다.
   measures가 기준 위반 블록(below_...)을 비워 두었다면 그 수치를 근거로 "부적합"이라고 답하지 않습니다.
   crvision-readable은 이미지 위 실제 글자가 읽힌다는 확인입니다. crvision-review와 visual_unresolved는 추가 확인이 필요하며, 다른 확정 위반이 없으면 E04/E05를 "판정 불가"로 답합니다.
4. block_ids에는 판단에 쓴 블록 id를 넣습니다. "판정 불가"는 비워도 됩니다.
5. reason은 한 문장입니다.
6. items의 모든 code에 대해 하나씩 답합니다."""

VISION_READABILITY_TASK = """These are cropped screenshots of rendered text blocks from a card product page.
Images appear in the exact order listed below. Judge only whether the text in each image is
comfortably distinguishable from its actual rendered background. Do not use a numeric threshold,
infer CSS values, decide legal compliance, or infer whether the block is hidden by default.
Return a compact JSON object keyed by block id, with a boolean readable value for every image.
"""
