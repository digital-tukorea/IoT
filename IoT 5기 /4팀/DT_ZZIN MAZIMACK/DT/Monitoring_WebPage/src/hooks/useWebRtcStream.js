import { useEffect, useMemo, useRef, useState } from 'react';

/**
 * ============================================================================
 *  CCTV 실시간 영상 훅 (WebRTC / WHEP)
 * ============================================================================
 *
 *  파이프라인:
 *
 *    IP 카메라 ──(RTSP)──▶ FastAPI + aiortc ──(WebRTC / WHEP)──▶ 이 <video>
 *
 *  MediaMTX 없이 server/main.py가 WHEP 엔드포인트 역할을 직접 합니다.
 *
 *  연결 순서:
 *    1) RTCPeerConnection 생성 + recvonly 영상 트랜시버 추가
 *    2) offer 생성 → setLocalDescription
 *    3) ICE 후보 수집이 끝날 때까지 대기 (aiortc는 trickle ICE/PATCH를 받지 않습니다)
 *    4) 완성된 SDP를 POST /api/whep → answer 수신
 *    5) setRemoteDescription → ontrack에서 <video>에 MediaStream 연결
 *    6) 언마운트 시 DELETE로 서버 세션 정리
 *
 *  @param {object}  opts
 *  @param {boolean} opts.enabled  false면 연결하지 않습니다.
 *                                 (aiortc는 시청자 1명당 인코더가 하나씩 돌기 때문에
 *                                  화면에 안 보이는 스트림은 꺼 두는 편이 좋습니다)
 *  @param {string}  opts.apiPath  이 서버 안의 어느 스트림에 붙을지 ('/api' = CCTV,
 *                                 '/api/robot' = 로봇캠). 둘 다 같은 서버(main.py)가
 *                                 StreamHub로 독립적으로 서빙합니다.
 */

// 서버 주소. 비워두면 같은 출처로 요청하고 Vite 프록시가 8000번으로 넘깁니다.
// ※ 프록시를 타는 건 시그널링(/api/whep)뿐이고, 영상 자체는 브라우저와 서버가
//    UDP로 직접 주고받습니다.
const API_BASE = import.meta.env.VITE_CCTV_BASE || '';

// 같은 LAN 안에서는 STUN 없이 붙습니다. 다른 네트워크에서 볼 때만 지정하세요.
const ICE_SERVERS = import.meta.env.VITE_STUN_URL
  ? [{ urls: import.meta.env.VITE_STUN_URL }]
  : [];

const STATUS_INTERVAL = 3000; // 상태 폴링 주기 (ms)
const RETRY_DELAY = 3000; // 연결 실패 시 재시도까지 (ms)
const ICE_TIMEOUT = 4000; // ICE 후보 수집 최대 대기 (ms)
const STALE_AFTER = 10; // 마지막 프레임이 이 초를 넘으면 '지연'으로 봅니다

/** ICE 후보 수집이 끝날 때까지 기다립니다. (타임아웃되면 모인 것만으로 진행) */
function waitForIceGathering(pc, timeoutMs) {
  if (pc.iceGatheringState === 'complete') return Promise.resolve();
  return new Promise((resolve) => {
    const finish = () => {
      pc.removeEventListener('icegatheringstatechange', check);
      clearTimeout(timer);
      resolve();
    };
    const check = () => {
      if (pc.iceGatheringState === 'complete') finish();
    };
    const timer = setTimeout(finish, timeoutMs);
    pc.addEventListener('icegatheringstatechange', check);
  });
}

/**
 * status 값:
 *   'idle'           비활성 (enabled=false)
 *   'connecting'     WebRTC 협상중 / 첫 프레임 대기
 *   'live'           정상 재생중
 *   'stale'          연결은 살아있으나 카메라 프레임이 안 들어옴
 *   'camera-offline' 서버는 살아있지만 카메라가 끊김
 *   'stream-error'   WebRTC 연결 실패
 *   'server-offline' 스트리밍 서버에 연결 불가
 */
export function useWebRtcStream({ enabled = true, apiPath = '/api' } = {}) {
  const videoRef = useRef(null);
  // 현재 세션 id. 상태 폴링에 실어 보내 서버에 "아직 보고 있다"고 알립니다.
  const sessionRef = useRef(null);
  const [health, setHealth] = useState(null); // /api/status 응답
  const [serverReachable, setServerReachable] = useState(true);
  const [attempt, setAttempt] = useState(0); // 재연결 시도 횟수

  // 연결 상태는 "몇 번째 시도의 결과인지"와 함께 들고 있습니다.
  // 그래야 재시도할 때 자동으로 'connecting'으로 되돌아갑니다.
  const [pcState, setPcState] = useState({ attempt: -1, value: 'connecting' });
  const pcValue = enabled && pcState.attempt === attempt ? pcState.value : 'connecting';

  // --- WebRTC 연결 ------------------------------------------------------
  useEffect(() => {
    if (!enabled) return undefined;

    let cancelled = false;
    let resourceUrl = null;
    const videoEl = videoRef.current; // 이 연결이 사용할 <video>. 정리할 때도 이걸 씁니다.
    const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS });

    pc.addEventListener('track', (event) => {
      if (videoEl) videoEl.srcObject = event.streams[0];
    });

    pc.addEventListener('connectionstatechange', () => {
      if (cancelled) return;
      if (pc.connectionState === 'connected') {
        setPcState({ attempt, value: 'live' });
      } else if (['failed', 'disconnected', 'closed'].includes(pc.connectionState)) {
        setPcState({ attempt, value: 'error' });
      }
    });

    // 서버 쪽 세션을 닫습니다. 이걸 빠뜨리면 서버가 시청자가 없는데도
    // 인코더를 계속 돌립니다. (서버도 연결 상태 변화로 회수하지만 한참 걸립니다)
    function releaseSession() {
      if (!resourceUrl) return;
      const url = `${API_BASE}${resourceUrl}`;
      resourceUrl = null;
      sessionRef.current = null;
      // keepalive를 켜야 페이지가 사라지는 중에도 요청이 끝까지 나갑니다.
      fetch(url, { method: 'DELETE', keepalive: true }).catch(() => {});
    }

    // 새로고침·탭 닫기·뒤로가기에서는 React의 정리 함수가 실행되지 않습니다.
    // 이걸 빠뜨리면 새로고침할 때마다 서버에 세션이 하나씩 쌓입니다.
    // (bfcache에 들어간 페이지는 PeerConnection이 살아있어 서버가 끊김을 감지하지 못합니다)
    const onPageHide = () => releaseSession();
    window.addEventListener('pagehide', onPageHide);

    async function connect() {
      try {
        pc.addTransceiver('video', { direction: 'recvonly' });
        await pc.setLocalDescription(await pc.createOffer());
        await waitForIceGathering(pc, ICE_TIMEOUT);
        if (cancelled) return;

        const res = await fetch(`${API_BASE}${apiPath}/whep`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/sdp' },
          body: pc.localDescription.sdp,
        });
        if (!res.ok) throw new Error(`WHEP ${res.status}`);

        resourceUrl = res.headers.get('Location');
        sessionRef.current = resourceUrl ? resourceUrl.split('/').pop() : null;
        const answerSdp = await res.text();
        if (cancelled) return; // 정리는 아래 cleanup이 connect() 종료 후에 처리합니다

        await pc.setRemoteDescription({ type: 'answer', sdp: answerSdp });
      } catch {
        if (!cancelled) setPcState({ attempt, value: 'error' });
      }
    }

    const started = connect();

    return () => {
      cancelled = true;
      window.removeEventListener('pagehide', onPageHide);
      if (videoEl) videoEl.srcObject = null;
      pc.close();
      // 세션 해제는 connect()가 끝난 뒤에 합니다.
      // POST 응답이 도착하기 전에 정리해버리면 방금 만들어진 세션의 주소를 모른 채
      // 지나가서 서버에 그대로 남습니다. (StrictMode의 이중 마운트에서 실제로 발생)
      started.finally(releaseSession);
    };
  }, [enabled, attempt, apiPath]);

  // --- 연결이 실패하면 잠시 후 재시도 -----------------------------------
  useEffect(() => {
    if (!enabled || pcValue !== 'error') return undefined;
    const id = setTimeout(() => setAttempt((n) => n + 1), RETRY_DELAY);
    return () => clearTimeout(id);
  }, [enabled, pcValue]);

  // --- 서버/카메라 상태 폴링 --------------------------------------------
  useEffect(() => {
    if (!enabled) return undefined;

    let cancelled = false;
    const controller = new AbortController();

    async function poll() {
      try {
        // 세션 id를 함께 보내는 것이 서버에 대한 하트비트입니다.
        // 이게 끊기면 서버가 20초 뒤 세션을 회수합니다.
        const query = sessionRef.current ? `?session=${sessionRef.current}` : '';
        const res = await fetch(`${API_BASE}${apiPath}/status${query}`, { signal: controller.signal });
        if (!res.ok) throw new Error(`status ${res.status}`);
        const data = await res.json();
        if (cancelled) return;
        setHealth(data);
        setServerReachable(true);
      } catch {
        if (cancelled) return;
        setHealth(null);
        setServerReachable(false);
      }
    }

    poll();
    const id = setInterval(poll, STATUS_INTERVAL);
    return () => {
      cancelled = true;
      controller.abort();
      clearInterval(id);
    };
  }, [enabled, apiPath]);

  const status = useMemo(() => {
    if (!enabled) return 'idle';
    if (!serverReachable) return 'server-offline';
    if (pcValue === 'error') return 'stream-error';
    if (health && !health.camera_connected) return 'camera-offline';
    if (health && health.seconds_since_frame > STALE_AFTER) return 'stale';
    if (pcValue === 'live') return 'live';
    return 'connecting';
  }, [enabled, serverReachable, health, pcValue]);

  return {
    videoRef,
    status,
    // WebRTC가 붙은 뒤로는 true. 카메라가 끊겨도 <video>는 계속 붙어 있습니다.
    hasVideo: pcValue === 'live',
    fps: health ? health.fps : 0,
    resolution: health ? health.resolution : null,
  };
}
