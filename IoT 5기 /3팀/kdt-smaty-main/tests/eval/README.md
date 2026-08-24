# 음성 intent 파라프레이즈 평가셋

같은 의도를 사람마다 다르게 말한다. "책상 좀 낮춰줘", "높이 내려줘",
"앉을 수 있게 해줘"는 모두 같은 결과를 기대하는 발화다. 이 평가셋은 그런
변형들을 모아, **model이 스스로 고른 tool과 인자**가 기대와 맞는지 측정한다.

`tests/unit/test_agents_tools.py`가 tool을 직접 호출해 계약을 검증하는 것과
목적이 다르다. 여기서는 tool을 직접 부르지 않는다. 발화만 주고 실제
`Runner.run()`이 무엇을 골랐는지 관찰한다.

## 구성

| 파일 | 역할 |
| --- | --- |
| `datasets/*.yaml` | 발화와 기대 tool·인자 |
| `schema.py` | 데이터셋 로딩과 채점 규칙 (`pyyaml`만 필요) |
| `fixtures.py` | 가짜 도메인 서비스와 turn context |
| `runner.py` | 실제 Agent 실행과 tool 호출 추출 |
| `scripts/eval_voice_intents.py` | opt-in 실행 스크립트 |
| `tests/unit/test_eval_datasets.py` | API 없이 도는 데이터셋 정합성 test |
| `baseline.py` / `baseline.json` | 측정한 실행을 굳히고 다음 실행과 대조 |
| `BASELINE.md` | 기준선 수치와 거기서 나온 제품 결함 |

## 무엇을 띄워야 하나

전체 서비스를 라즈베리파이나 서버에 올릴 필요가 없다. 이 평가는 Agent와
tool만 조립하고 나머지 도메인 서비스는 전부 fake로 바꾼다. 그래서 앱을
실행하지 않은 개발 PC에서 그대로 돌아간다.

| 켜지 않아도 되는 것 | 이유 |
| --- | --- |
| 앱 프로세스, FastAPI/uvicorn | 평가가 Agent를 직접 조립한다 |
| MQTT broker | `_Automation` fake가 대신한다 |
| ESP32 시리얼, 책상·틸트 하드웨어 | 같은 fake가 호출만 기록한다 |
| WLED 장치 | `_Wled` fake가 대신한다 |
| 카메라, 마이크, 스피커 | STT/TTS 없이 텍스트 발화만 넣는다 |
| SQLite, Mem0 | 작업 모드·기억도 fake다 |
| `SMART_DESK_*` 앱 설정 | API key는 환경변수에서 직접 읽는다 |

실제로 나가는 외부 호출은 OpenAI API 하나뿐이다.

**설치와 실행은 구분해야 한다.** 이 프로젝트의 package `__init__`들이 하위
모듈을 즉시 re-export해서, assistant tool 하나만 import해도 `cv2`, `aiomqtt`,
`pyserial`이 import 그래프에 딸려온다. 그래서 이 패키지들이 *설치*는 돼 있어야
한다. 하지만 broker에 접속하거나 카메라를 열지는 않는다. 필요한 것은 base
dependency와 `voice` extra(`openai-agents`, `openai`), 그리고 `pyyaml`이다.
발화 목록만 보는 `--list`는 `pyyaml`만 있으면 된다.

이 성질은 일부러 유지한다. 무언가를 검증하려고 책상 전체를 켜야 한다면, 운영
중인 장비를 건드릴 위험이 생기고 확인도 느려진다. `tests/unit/test_eval_datasets.py`의
`test_eval_context_is_wired_only_to_fakes`가 turn context에 진짜 서비스가
섞여 들어오지 않는지 지킨다.

## 실행

OpenAI API를 호출하므로 CI에서 상시 실행하지 않는다. 필요할 때만 돌린다.

```bash
export SMART_DESK_OPENAI__API_KEY=sk-...

# 발화 목록만 확인 (API 호출 없음)
python scripts/eval_voice_intents.py --list

# 20개만 표본으로
python scripts/eval_voice_intents.py --shuffle --limit 20

# 특정 tool만, 리포트 저장
python scripts/eval_voice_intents.py --tool set_activity_mode --report data/eval/modes.json

# 전체 실행 + 실패율 임계값
python scripts/eval_voice_intents.py --max-failure-rate 0.1
```

임계값을 주지 않으면 결과를 보고만 하고 항상 0으로 끝난다. `--report`는
발화별 실제 호출까지 담은 JSON을 남기므로 회귀 비교에 쓸 수 있다.

## 기준선과 회귀 비교

실패율 하나만 보면 좋아졌는지 알 수 없다. 같은 7.2%라도 고쳐진 발화와 새로
깨진 발화가 맞바꿔진 것일 수 있다. 그래서 `baseline.json`에 **발화 단위**로
통과 여부를 저장하고, 실행할 때마다 무엇이 뒤집혔는지 본다.

실행하면 자동으로 대조한다.

```
기준선 대비 변화
  회귀 없음
  개선 1건
    ✓ 기울기 최대로  (set_tilt_level: args_mismatch → 통과)
  tool별 실패 수 변화 (기준선 → 이번)
    set_tilt_level             2 → 1 / 32건  (개선)
  같은 발화 48건 기준 실패율 4.2% → 2.1% (-2.1%)
```

| 옵션 | 뜻 |
| --- | --- |
| `--no-baseline` | 대조를 건너뛴다 |
| `--baseline PATH` | 다른 기준선 파일과 비교 |
| `--fail-on-regression` | 통과하던 발화가 깨지면 종료 코드 1 |
| `--update-baseline` | 이번 결과를 새 기준선으로 저장 (전체 실행에서만) |

case는 발화 문자열로 식별한다. `dataset[index]`는 발화를 하나 끼워 넣기만 해도
뒤 번호가 전부 밀려 기준선이 통째로 어긋난다.

일부만 돌렸을 때(`--tool`, `--dataset`, `--limit`)의 실패율은 **양쪽에 모두 있는
발화로만** 계산한다. 250건짜리 기준선 실패율을 63건짜리 이번 실패율과 나란히
놓으면 비교가 되지 않기 때문이다. 같은 이유로 이때는 안 돌린 발화를 "사라졌다"고
보고하지 않는다.

기준선을 갱신할 때는 그 실행이 대표성이 있는지 먼저 본다. model이나
`<profile_memory>` 시드가 달라진 실행을 굳히면 이후 비교가 전부 어긋난다.

### 같은 발화가 실행마다 뒤집힐 수 있다

model 응답은 결정적이지 않다. 실제로 `기울기 최대로`는 한 실행에서 실패하고
다음 실행에서 통과했다. 회귀 한 건이 떴다고 바로 코드를 의심하기보다, 그
발화만 다시 돌려 재현되는지 확인하는 편이 낫다.

```bash
python scripts/eval_voice_intents.py --tool set_tilt_level --no-baseline
```

## 데이터셋 형식

```yaml
- utterance: "책상 75센티로 맞춰줘"
  expected_tool: set_desk_target
  expected_args_match: {height_cm: 75}
```

| key | 필수 | 설명 |
| --- | --- | --- |
| `utterance` | O | 사용자가 실제로 할 법한 발화 |
| `expected_tool` | O | 이 발화가 불러야 하는 tool |
| `expected_args_match` | | 부분 일치로 검사할 인자. 적지 않은 인자는 자유 |
| `accept_also` | | 제품상 똑같이 옳은 대안 tool 이름 |
| `notes` | | 왜 이 기대값인지에 대한 메모 |

인자 matcher는 세 가지다.

- 값 그대로: `{height_cm: 75}` — 실수는 오차를 허용하고 문자열은 대소문자를 무시한다
- 범위: `{brightness: {min: 240, max: 255}}` — "최대한 밝게"처럼 정답이 한 값이 아닐 때
- 후보: `{color_hex: {any_of: ["FFA500", "FF8000"]}}` — 주황색처럼 표현이 여럿일 때

## 채점 규칙

기대한 tool이 **호출됐고 인자가 맞으면** 통과다. `request_followup`,
`list_activity_modes`, `get_tilt_state` 같은 보조 tool이 함께 불려도
오답으로 보지 않는다. 사용자의 의도를 이루는 정상 경로이기 때문이다.

실패는 세 가지로 구분해 보고한다.

- `tool_not_called` — 다른 tool을 골랐거나 아무것도 안 골랐다
- `args_mismatch` — tool은 맞는데 인자가 틀렸다
- `run_error` — SDK·네트워크 오류나 시간 초과. model의 오답과 구분한다

## 기대값을 정한 근거

- **높이 조회 tool이 없다.** 그래서 "조금만 낮춰줘"처럼 목표 수치가 없는
  상대 명령은 `hold_desk`가, 수치가 있으면 `set_desk_target`이 정답이다.
- **작업 모드 key는 불투명하다.** 실제 key는 `mode-<32자리 hex>`라 model이
  이름만 듣고 알 수 없다. `list_activity_modes`로 조회한 뒤 골라야 하고,
  fixture도 사람이 못 읽는 key를 써서 그 2단계를 실제로 검증한다.
- **기억은 명시적 요청일 때만.** 그래서 "오늘 좀 피곤하네" 같은 일반 대화를
  일부러 넣어 `remember_fact` 과잉 호출을 잡는다.

## 데이터셋을 고칠 때

발화를 추가하거나 기대값을 바꾸면 먼저 무료 test부터 돌린다.

```bash
pytest tests/unit/test_eval_datasets.py
```

없는 tool 이름, 없는 인자, fixture에 없는 모드 key와 효과 id, 중복 발화를
API 호출 없이 잡아준다.

평가에서 실패한 발화가 사실은 **model이 옳고 기대값이 틀린** 경우도 있다.
그때는 model에 맞추기 전에 어느 쪽이 제품으로서 옳은지 먼저 정하고,
기대값을 바꾼다면 `notes`에 이유를 남긴다.
