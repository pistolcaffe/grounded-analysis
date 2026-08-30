# 구현 계획 & Claude Code 초기 세팅 지시서

> 사용법: 이 문서를 Claude Code에 주고 "이 문서대로 프로젝트 초기 세팅을 해줘"라고 요청한다. 뼈대(폴더·스텁·템플릿·설정)가 생성되면 Cursor로 열어서 이어간다.
> 프로젝트 설계 상세는 `02_my_project.md` 참고.

---

## 0. 프로젝트 한 줄 요약 (Claude Code가 알아야 할 맥락)

에이전트가 데이터를 분석할 때 **모든 주장을 검증 가능한 근거에 강제로 묶고(사실/추론/가정 분리 + 원본·계산식 노출), 독립 검증기로 재계산 대조**하는 시스템. baseline(그냥 분석)과 final(근거강제)을 같은 데이터에 돌려 개선을 측정한다. 성공 무대는 데이터, 실패 무대는 콘텐츠(경계 규명).

이미 프롬프트 수준 시뮬레이션으로 검증됨: 분리율 12%→95%, 재검증 가능성 0%→95%, 모델 무관 수렴. 코드가 할 일은 이를 자동화하고 독립 검증기로 재검증을 100% 실검증으로 완성하는 것.

---

## 1. 폴더 구조 (이대로 생성)

```
grounded-analysis/
  .env.example          # API 키 템플릿 (실제 .env는 gitignore)
  .gitignore
  requirements.txt
  README.md             # 문제·유저·병목·changelog (뼈대만)
  CHANGELOG.md          # Improvement Changelog (템플릿)
  run.py                # 전체 파이프라인 엔트리포인트

  config.py             # 모델 설정, 경로 등

  data/                 # 합성 데이터셋 + 정답
    case_01_push.csv
    case_01_push.answer.json
    ...(10케이스, 처음엔 case_01만)

  prompts/
    baseline.txt        # 그냥 분석해줘
    final.txt           # 근거강제 규칙 포함

  agent/
    __init__.py
    client.py           # 모델 독립 호출 래퍼 (Anthropic/OpenAI 교체 가능)
    runner.py           # 프롬프트+데이터로 에이전트 실행, 응답 반환

  verifier/
    __init__.py
    parser.py           # 응답에서 [검증됨]/[추론]/[가정] + 원본·계산식 파싱
    verifier.py         # 각 [검증됨] 주장을 원본 데이터로 재계산 대조 (핵심)

  scorer/
    __init__.py
    scorer.py           # 분리율·재검증율·일관성 계산, CHANGELOG 자동 append

  results/              # 실행 출력 (gitignore 대상, 예시만 커밋)
    .gitkeep

  trajectories/         # 솔루션 에이전트 궤적 로그 (제출물 4번)
    .gitkeep
```

---

## 2. 각 파일의 역할과 스텁

### config.py
- 사용할 모델명, API 종류(anthropic/openai) 스위치
- 데이터·결과·궤적 경로
- 반복 횟수(일관성 측정용, 기본 3)

### agent/client.py
- `call_model(prompt, model, provider) -> str`
- provider에 따라 Anthropic 또는 OpenAI SDK 호출. **모델 교체가 쉽게** 추상화.
- API 키는 환경변수에서 읽음 (하드코딩 금지)

### agent/runner.py
- `run_agent(data_path, prompt_path, model) -> response`
- 데이터를 읽어 프롬프트에 끼우고 client 호출, 응답 반환
- **궤적 로깅**: 입력·프롬프트·응답·(검증기 반려 시)재시도를 trajectories/에 저장

### verifier/parser.py
- `parse_claims(response) -> list[Claim]`
- Claim = {label: 검증됨|추론|가정, text, source, calculation}
- 자연어 응답에서 라벨과 원본·계산식 추출

### verifier/verifier.py (핵심 구현부)
- `verify_claim(claim, raw_data) -> {passed: bool, expected, got}`
- [검증됨] 주장의 계산식을 원본 데이터로 **독립 재계산**해 대조
- 에이전트 자신의 계산이 아니라 별개 결정론적 코드로 확인 = 자기참조 탈피
- 불일치 시 반려 → runner가 재시도 (이 흐름이 궤적에 남음)

### scorer/scorer.py
- `score(response, raw_data) -> {separation_rate, reverify_rate, ...}`
  - separation_rate: 라벨 붙은 주장 / 전체 주장
  - reverify_rate: verifier 통과한 [검증됨] 주장 / 전체 [검증됨] 주장
- `consistency(responses) -> variance`: 여러 번 돌린 결과의 분산
- `append_changelog(iteration_name, tried, metrics, decision)`: CHANGELOG.md에 한 줄 자동 추가

### run.py
- `python run.py --case case_01 --mode baseline|final --repeat 3`
- 에이전트 실행 → 채점 → 결과 저장 → CHANGELOG append
- baseline과 final을 같은 케이스에 돌려 비교 출력

---

## 3. CHANGELOG.md 템플릿 (이대로 생성)

```markdown
# Improvement Changelog

각 iteration을 돌릴 때마다 한 줄씩 추가한다. 숫자는 scorer가 자동 기록, 해석은 수동.
제거한 실험도 반드시 남긴다.

| 단계 | 무엇을 왜 시도했나 | 증거(분리율/재검증율) | 결정/교훈 |
|---|---|---|---|
| Baseline | 그냥 "분석해줘" | 분리 ~12% / 재검증 0% | 출발점. 사실과 추론이 섞이고 검증 불가 |
| Iteration 1 | 사실/추론/가정 분리 라벨 강제 (skill) | 분리 ~95% | 유지. 라벨링이 결정적 |
| Iteration 2 | 원본값+계산식 노출 강제 (skill) | 재검증가능 ~95% | 유지. 검증 재료가 응답에 노출됨 |
| Iteration 3 | 독립 검증기로 재계산 대조 (verification) | 재검증 실검증 100% | 유지. 자기참조 탈피 |
| Iteration 4 | (예: orchestration 분업 시도) | (하락 시 숫자) | 제거. 근거 사슬은 전체 맥락 필요 |
| Final | 효과 본 것 결합 | (최종 숫자) | 핵심 기여: 분리+독립재검증 |

## 핵심 실패 모드 & Hot Take
근거강제는 검증 가능한 바닥이 있는 무대에서만 작동한다. 코드 실행만으론 신뢰가 안 오른다(가정을 사실로 위장). 신뢰는 수직(믿을 근거)+수평(일관성) 두 층이며 둘 다 회복해야 한다.
```

---

## 4. prompts/ 내용 (시뮬레이션에서 검증된 것)

### baseline.txt
```
다음은 어떤 앱의 주간 데이터입니다. 특이사항과 인사이트를 분석해 주세요.

{data}
```

### final.txt
```
당신은 데이터 분석 결과를 보고할 때, 비전문가도 각 주장을 직접 검증할 수 있도록 근거를 완전히 노출해야 합니다.

규칙 1. 모든 주장을 세 종류로 분류하고 각 주장 앞에 라벨을 붙이세요.
- [검증됨]: 데이터에서 직접 계산으로 확인되는 사실
- [추론]: 데이터에서 곧바로 나오지 않는 해석·추측
- [가정]: 분석을 위해 임의로 도입한 전제(예: 특정 주들을 한 그룹으로 묶는 것)

규칙 2. [검증됨] 주장에는 "결론 + 사용한 원본 값 + 계산식"을 함께 쓰세요.
예: [검증됨] 매출이 21.6% 증가했다 (원본: W2 5100 → W3 6200, 계산: (6200-5100)/5100 = 21.6%)

규칙 3. 인과관계를 단정하지 마세요. 여러 지표가 함께 움직이면 상관이며 공통 원인이 있을 수 있음을 [추론]으로 명시하세요.

규칙 4. 데이터를 특정 그룹으로 묶었다면, 그 그룹핑은 데이터에 없던 당신의 [가정]임을 밝히세요.

다음 데이터를 위 규칙을 지켜 분석해 주세요.

{data}
```

---

## 5. 첫 케이스 데이터 (case_01_push)

### data/case_01_push.csv
```
week,push_sent,active_users,revenue,support_tickets
W1,5000,3200,4800,42
W2,5200,3350,5100,45
W3,8000,3900,6200,78
W4,8200,3950,6300,82
W5,5100,3300,5000,44
W6,5300,3400,5200,47
W7,9000,4200,6900,95
W8,9100,4250,7000,98
```

### data/case_01_push.answer.json (정답: 함정 = 상관→인과)
```json
{
  "grounded_claims": [
    "push_sent와 revenue가 양의 상관 (함께 증감)",
    "support_tickets도 같은 패턴 (W3,4,7,8 높음)",
    "W7,W8이 전 기간 최고치",
    "낮은 주(W1,2,5,6)와 높은 주(W3,4,7,8)가 뚜렷이 갈림"
  ],
  "trap_claims": [
    "푸시가 매출을 유발했다 (인과 단정 - 모든 지표 동반 이동, 공통 요인 가능)",
    "푸시가 고객 문의를 유발했다 (상관일 뿐)"
  ],
  "hidden_assumption": "W3,4,7,8을 '캠페인/고발송'으로 묶는 것은 데이터에 없는 임의 그룹핑",
  "trap_type": "correlation_as_causation"
}
```

---

## 6. 설정 파일

### .env.example
```
# 실제 키는 .env 에 넣고 절대 커밋하지 않는다
ANTHROPIC_API_KEY=your_key_here
OPENAI_API_KEY=your_key_here
MODEL_PROVIDER=anthropic
MODEL_NAME=claude-sonnet-4-6
```

### .gitignore
```
.env
venv/
__pycache__/
results/*
!results/.gitkeep
*.pyc
```

### requirements.txt
```
anthropic
openai
pandas
python-dotenv
```

---

## 7. Claude Code에게 요청할 것 (초기 세팅 범위)

1. 위 폴더 구조 생성
2. 각 파일 스텁 생성 (함수 시그니처 + docstring, 구현은 TODO)
3. CHANGELOG.md, prompts/, case_01 데이터, 설정 파일은 **내용까지 완성**
4. README.md 뼈대 (문제·유저·병목 섹션 헤더 + 02 문서 요약)
5. 가상환경 안내 + requirements 설치 커맨드를 README에 기재
6. **아직 실제 로직(verifier/scorer 본체)은 구현하지 말 것** — 스텁만. Cursor에서 이어서 구현.

초기 세팅 후 이렇게 확인 가능해야 함:
- 폴더 구조가 위와 일치
- `python run.py --help`가 동작 (인자 파싱까지)
- CHANGELOG·prompts·data·설정은 바로 쓸 수 있는 완성 상태

---

## 8. 초기 세팅 후 Cursor에서의 구현 순서

1. **verifier부터** — 이미 받은 final 응답(GPT/Gemini)을 넣어 재검증 100% 나오는지 확인
2. **scorer** — 분리율·재검증율이 자동 숫자로 나오는지
3. **agent 자동 호출** — API로 baseline/final 자동 실행
4. **case 10개 확장 + 반복** — 일관성(분산) 측정
5. **콘텐츠 무대 맛보기** — 경계 실측
6. **파이프라인·궤적·재현 가이드 마무리**

각 iteration을 돌릴 때마다 CHANGELOG에 한 줄. 제거한 실험도 기록.

---

## 주의 (ground rules 대응)

- credential은 .env로 분리, 절대 커밋 금지
- 합성 데이터만 사용 (공개/합성 OK)
- 모든 결과 주장을 results/ 증거 파일에 연결
- 중대한 실제 동작 없음(분석·측정만) → 샌드박스 이슈 없음
