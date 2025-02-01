import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import moment from 'moment';
import 'moment/locale/zh-cn';  // 导入中文语言包
import { API_BASE_URL } from '../config';
import './DeviceMonitor.css';

// 设置 moment 为中文
moment.locale('zh-cn');

function DeviceMonitor({ deviceId, pollInterval }) {
  const [screenshot, setScreenshot] = useState(null);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [isOnline, setIsOnline] = useState(true);
  const [error, setError] = useState(null);

  const fetchScreenshot = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/screenshots`, {
        params: { deviceId }
      });

      const { url, uploadTime } = response.data;
      
      // 将UTC时间转换为本地时间
      const localUploadTime = moment.utc(uploadTime).local();
      
      // 检查设备是否在线（3分钟内有更新）
      const isDeviceOnline = moment().diff(localUploadTime, 'minutes') < 3;
      
      setScreenshot(url);
      setLastUpdate(localUploadTime);
      setIsOnline(isDeviceOnline);
      setError(null);
    } catch (err) {
      setError(err.response?.data?.message || '获取截图失败');
      if (err.response?.status === 404) {
        setIsOnline(false);
      }
    }
  }, [deviceId]);

  useEffect(() => {
    // 初始加载
    fetchScreenshot();

    // 设置轮询（每分钟检查一次）
    const intervalId = setInterval(fetchScreenshot, 60000);

    return () => clearInterval(intervalId);
  }, [fetchScreenshot]);

  const formatDateTime = (time) => {
    if (!time) return '';
    return time.format('YYYY年MM月DD日 HH:mm:ss');
  };

  return (
    <div className={`device-monitor ${isOnline ? 'online' : 'offline'}`}>
      <h2>设备 {deviceId}</h2>
      <div className="status">
        状态: <span className={`status-indicator ${isOnline ? 'online' : 'offline'}`}>
          {isOnline ? '在线' : '离线'}
        </span>
      </div>
      {error ? (
        <div className="error">{error}</div>
      ) : screenshot ? (
        <div className="screenshot-container">
          <img 
            src={screenshot} 
            alt={`Screenshot from ${deviceId}`}
            style={{ maxWidth: '100%' }}
          />
          <div className="timestamp">
            最后更新: {formatDateTime(lastUpdate)}
          </div>
          <div className="relative-time">
            {lastUpdate && `(${lastUpdate.fromNow()})`}
          </div>
        </div>
      ) : (
        <div className="loading">加载中...</div>
      )}
    </div>
  );
}

export default DeviceMonitor; 