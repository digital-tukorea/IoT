import { useMonitoringDashboard } from './hooks/useMonitoringDashboard';
import LoginScreen from './components/LoginScreen';
import Dashboard from './components/dashboard/Dashboard';
import DetailModal from './components/modals/DetailModal';
import CctvModal from './components/modals/CctvModal';
import EventLogModal from './components/modals/EventLogModal';
import Toast from './components/Toast';
import './App.css';

export default function App() {
  const model = useMonitoringDashboard('login');
  const { screen, detailOpen, detailEvent, cctvOpen, logOpen, eventLog, toast, actions } = model;

  return (
    <div className="app-frame">
      {screen === 'login' && <LoginScreen onLogin={actions.goDashboard} />}

      {screen === 'dashboard' && <Dashboard model={model} />}

      {detailOpen && (
        <DetailModal event={detailEvent} onClose={actions.closeDetail} onConfirm={actions.confirmEvent} />
      )}

      {cctvOpen && <CctvModal label="CCTV · 실시간" onClose={actions.closeCctv} />}

      {logOpen && <EventLogModal rows={eventLog} onClose={actions.closeLog} />}

      <Toast message={toast} />
    </div>
  );
}
