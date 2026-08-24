# intent 평가 기준선

**측정일:** 2026-08-19 · **model:** `gpt-5.6-terra` / reasoning `low` (운영 기본값)
**조건:** 발화 250건, 동시 실행 6, hosted web search 포함, 운영과 동일한
`<profile_memory>` 주입

| 지표 | 값 |
| --- | --- |
| 전체 | 250 |
| 통과 | 232 |
| 실패 | 18 |
| 실패율 | 7.2% |
| 소요 | 191초 |

실패 사유는 `tool_not_called` 16건, `args_mismatch` 2건이고 `run_error`는 없었다.
이후 노란색 기대값을 골드 계열까지 넓혀 WLED 데이터셋은 63건 전부 통과한다.

무실패 tool: `set_desk_target`(32), `set_wled_brightness`(12), `set_wled_color`(14),
`set_wled_effect`(8), `turn_wled_on`/`turn_wled_off`(각 10), `stop_desk`(8),
`stop_tilt`(8), `get_tilt_state`(8), `remember_fact`(10), `forget_fact`(5),
`list_activity_modes`(6), `get_wled_state`(5), `get_wled_capabilities`(4).

## 고쳐야 할 제품 결함

평가가 실제로 잡아낸 것들이다. 평가셋이 아니라 제품 쪽을 고쳐야 한다.

### 1. 틸트 tool의 선언 범위가 장치 실제 범위와 다르다

`set_tilt_level`의 스키마는 `ge=0, le=10`인데 이 책상의 실제 허용 범위는
`tilt_level_range`(기본 0~3)다. "기울기 최대로"에서 model이 스키마를 믿고
`level=10`을 보내 `tilt_level_out_of_range`로 실패했다. 실제 음성에서도 똑같이
실패한다.

지시문은 범위가 필요하면 `get_tilt_state`를 부르라고 하지만, 스키마에 10이
적혀 있으면 model이 굳이 확인하지 않는다. tool 설명에 "허용 범위는 책상마다
다르므로 `get_tilt_state`로 확인해야 한다"를 넣거나, 스키마 상한을 실제 범위로
좁히는 편이 확실하다.

### 2. "스탠딩 모드"가 작업 모드 전환이 아니라 높이 변경으로 처리된다

"스탠딩 모드 켜줘", "스탠딩 모드로 전환해줘"에서 model이 `set_activity_mode`
대신 `set_desk_target(110)`을 불렀다. 장기 기억의 선호 높이를 쓴 것이라
높이 자체는 맞지만, 그 모드의 조명과 틸팅 설정은 적용되지 않는다. 사용자가
"모드"라고 명시했을 때는 모드 전환이어야 한다.

## 기대값을 다시 볼 후보

model이 틀렸다고 단정하기 어려운 것들이다. 제품 판단이 필요하다.

| 발화 유형 | 기대 | 실제 | 쟁점 |
| --- | --- | --- | --- |
| "기본으로 초기화해줘" 등 4건 | `set_activity_mode(default)` | 무엇을 초기화할지 되물음 | 높이·틸팅·조명 중 무엇인지 실제로 모호하다 |
| "책상이 낮은 것 같아" 등 4건 | `hold_desk` | 기억된 선호 높이를 제시하며 확인 | 기억이 있으면 되묻는 쪽이 더 안전할 수 있다 |
| "좀 쉴게", "쉬는 분위기로" 2건 | `set_activity_mode(휴식)` | 조명만 조정하거나 되물음 | 간접 발화를 모드 전환으로 볼지 |
| "알아서 높이 조절해줘" | `set_control_mode(auto)` | 앉을지 설지 되물음 | AUTO 전환 대 즉시 조절 |
| "작업 모드가 뭐야?" | `request_followup` | 잘 설명했으나 미호출 | 지시문은 질문에 호출하라고 되어 있다 |

## 재현과 비교

이 수치는 `baseline.json`에 발화 단위로 저장돼 있다. 실행하면 자동으로 대조해
무엇이 뒤집혔는지 보여준다.

```bash
# 전체 실행 + 회귀가 있으면 종료 코드 1
python scripts/eval_voice_intents.py --concurrency 6 --fail-on-regression

# 기준선을 이번 실행으로 갱신
python scripts/eval_voice_intents.py --concurrency 6 --update-baseline \
  --baseline-note "틸트 범위 수정 후 재측정"
```

기준선을 갱신하기 전에 model과 `<profile_memory>` 시드가 같은지 확인한다. 둘 중
하나만 달라져도 실패율이 크게 움직인다. 실제로 `<profile_memory>` 주입을
빠뜨렸을 때는 같은 데이터셋에서 실패율이 11.6%였고, 특히 `set_desk_target`이
34.4%였다가 주입 후 0%가 됐다.

## 이 수치를 읽을 때 주의할 점

**model 응답은 결정적이지 않다.** 위 표의 `기울기 최대로`는 기준선 측정에서
`args_mismatch`였지만 직후 재실행에서는 통과했다. 실패 한 건을 곧바로 회귀로
단정하지 말고 해당 발화만 다시 돌려 재현되는지 본다. 뒤집어 말하면, 위 결함
목록 중 재현율이 낮은 항목은 "가끔 실패"에 가깝다.

**노란색 기대값은 기준선 측정 이후에 고쳤다.** 그래서 기준선에는
`노란색으로 해줘`가 실패로 남아 있고, 다음 실행에서 개선 1건으로 잡힌다.
전체를 다시 돌려 `--update-baseline`을 하면 정리된다.
