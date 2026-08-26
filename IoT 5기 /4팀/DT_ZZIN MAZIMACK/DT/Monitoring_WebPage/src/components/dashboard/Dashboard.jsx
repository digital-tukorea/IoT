import TopBar from './TopBar';
import SensorPanel from './SensorPanel';
import PlanPanel from './PlanPanel';
import EventPanel from './EventPanel';

/** Dashboard layout: header + 3-column monitoring grid. */
export default function Dashboard({ model }) {
  const { head, zones, robot, events, actions } = model;

  // aiortc는 시청자 1명당 인코더를 돌리므로 스트림을 겹쳐 띄우지 않습니다.
  // CCTV 팝업/이벤트 상세가 열려 있으면 평면도 썸네일 스트림을 끕니다.
  const planCctvEnabled = !model.cctvOpen && !model.detailOpen;

  return (
    <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column' }}>
      <TopBar head={head} onLogout={actions.goLogout} />

      <div style={{ flex: 1, display: 'grid', gridTemplateColumns: '264px 1fr 300px', minHeight: 0 }}>
        <SensorPanel zones={zones} />
        <PlanPanel
          zones={zones}
          robot={robot}
          onOpenCctv={actions.openCctv}
          cctvEnabled={planCctvEnabled}
        />
        <EventPanel
          events={events}
          onOpenDetail={actions.openDetail}
          onConfirm={actions.confirmEvent}
          onOpenLog={actions.openLog}
        />
      </div>
    </div>
  );
}
