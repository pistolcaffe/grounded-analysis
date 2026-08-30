# Grounded Analysis

에이전트 판단의 신뢰 경계를 규명하는 시스템 — 모든 주장을 검증 가능한 근거에 강제로 묶고, 독립 검증기로 재계산 대조한다.

---

## 문제

실행 전엔 검증 못 하고 실행하면 되돌릴 수 없는 판단 작업에서, 검증 능력 없는 사람은 에이전트 결론을 맹신하게 된다. 아는 사람은 안 속고 모르는 사람만 속는데, 에이전트가 필요한 건 정작 모르는 사람이다.

## 유저

에이전트에게 판단·해석을 맡기는 실무자. 특히 **그 분야를 잘 모르는 사람** — 데이터를 주고 "인사이트 뽑아줘"를 묻는 비전문가.

## 병목

에이전트가 그럴듯한 판단을 술술 내놓는데:
- **수직 신뢰 붕괴**: 실제 근거에서 나온 건지 지어낸 건지 알 수 없다.
- **수평 신뢰 붕괴**: 같은 데이터에 물을 때마다 답이 다르다.

다시 검증하지 않으면 못 믿고, 검증하면 에이전트를 쓸 이유가 없다.

## 해결 접근

1. **사실/추론/가정 분리** — 모든 주장을 `[검증됨]` / `[추론]` / `[가정]`으로 라벨링 강제
2. **근거 사슬 강제** — `[검증됨]` 주장에 원본 값 + 계산식 노출 요구
3. **독립 검증기** — 에이전트와 별개의 결정론적 코드로 수치를 원본 데이터에서 재계산·대조 (자기참조 탈피)

**경계 (핵심)**: 검증 가능한 바닥이 있는 무대(데이터)에선 작동하고, 바닥이 없는 무대(콘텐츠)에선 무너진다. 이 경계 자체가 "AI 판단을 믿어도 되는 조건"을 정의한다.

## 실측 결과 (프롬프트 시뮬레이션)

| | Baseline | Final |
|---|---|---|
| 분리율 | ~12% | ~95% |
| 재검증 가능성 | ~0% | ~95% |
| 인과 태도 | 단정~유보 (모델마다 다름) | 거부 (모델 무관 수렴) |

독립 검증기 코드 완성 시 재검증 실검증 **100%** 예정.

---

## 설치

```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

API 키 설정:

```bash
cp .env.example .env
# .env 열어서 ANTHROPIC_API_KEY 또는 OPENAI_API_KEY 입력
```

## 사용법

```bash
# 도움말
python run.py --help

# baseline + final 각 3회 실행 및 채점
python run.py --case case_01 --mode both --repeat 3

# baseline만
python run.py --case case_01 --mode baseline

# final만, 5회 반복
python run.py --case case_01 --mode final --repeat 5
```

## 프로젝트 구조

```
grounded-analysis/
  run.py              # 파이프라인 엔트리포인트
  config.py           # 모델·경로 설정
  agent/              # 모델 호출 래퍼 (provider 교체 가능)
  verifier/           # 응답 파싱 + 독립 재계산 검증기
  scorer/             # 분리율·재검증율·일관성 채점 + CHANGELOG 자동 기록
  data/               # 합성 데이터셋 + 정답
  prompts/            # baseline.txt / final.txt
  results/            # 실행 출력 (gitignore)
  trajectories/       # 에이전트 궤적 로그
```

변경 이력은 [CHANGELOG.md](CHANGELOG.md) 참조.
