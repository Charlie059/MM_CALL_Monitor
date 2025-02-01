import React, { useState } from 'react';
import DeviceMonitor from './components/DeviceMonitor';
import './App.css';

function App() {
  const [pollInterval, setPollInterval] = useState(15); // 默认15分钟刷新
  const devices = ['device-001']; // 设备列表

  return (
    <div className="App">
      <header className="App-header">
        <h1>设备监控系统</h1>
        <div className="settings">
          <label>
            刷新间隔（分钟）：
            <select 
              value={pollInterval} 
              onChange={(e) => setPollInterval(Number(e.target.value))}
            >
              <option value={1}>1</option>
              <option value={5}>5</option>
              <option value={15}>15</option>
              <option value={30}>30</option>
            </select>
          </label>
        </div>
      </header>
      <main className="App-main">
        {devices.map(deviceId => (
          <DeviceMonitor 
            key={deviceId}
            deviceId={deviceId}
            pollInterval={pollInterval}
          />
        ))}
      </main>
    </div>
  );
}

export default App; 