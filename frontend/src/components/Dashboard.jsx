import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import toast from 'react-hot-toast';
import { 
  FaTint, FaUpload, FaChartLine, FaHistory, FaSignOutAlt, FaSync, 
  FaClock, FaBell, FaExclamationTriangle, FaCheckCircle, 
  FaThermometerHalf, FaTachometerAlt, FaFlask, FaWater,
  FaArrowUp, FaArrowDown, FaMinus
} from 'react-icons/fa';
import DataUpload from './DataUpload';
import Results from './Results';
import { db } from '../firebase';
import { collection, onSnapshot, query, orderBy, limit } from 'firebase/firestore';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Area,
  AreaChart
} from 'recharts';

const Dashboard = ({ setIsAuthenticated }) => {
  const [user, setUser] = useState(null);
  const [stats, setStats] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [refreshInterval, setRefreshInterval] = useState(5);
  const [historyData, setHistoryData] = useState([]);
  const [liveReadings, setLiveReadings] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [alerts, setAlerts] = useState([]);
  const [currentParams, setCurrentParams] = useState({
    ph: 7.2,
    temperature: 22.5,
    do: 8.1,
    turbidity: 2.3
  });
  
  const navigate = useNavigate();
  const token = localStorage.getItem('token');

  useEffect(() => {
    const userData = localStorage.getItem('user');
    if (userData) {
      setUser(JSON.parse(userData));
    }

    fetchStats();
    fetchLiveReadings();
    fetchAlerts();

    // Fetch Firebase history
    axios.get('http://localhost:8000/api/firebase/history', {
      headers: { Authorization: `Bearer ${token}` }
    })
    .then(res => setHistoryData(res.data))
    .catch(err => console.log(err));

    // Live Firebase listener for readings
    const readingsQuery = query(
      collection(db, "live_readings"),
      orderBy("timestamp", "desc"),
      limit(50)
    );
    
    const unsubscribeReadings = onSnapshot(readingsQuery, (snapshot) => {
      const liveData = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
        timestamp: doc.data().timestamp?.toDate?.() || new Date(doc.data().timestamp)
      }));
      setLiveReadings(liveData);
      if (liveData.length > 0) {
        const latest = liveData[0];
        setCurrentParams({
          ph: latest.ph || 7.2,
          temperature: latest.temperature || 22.5,
          do: latest.do || 8.1,
          turbidity: latest.turbidity || 2.3
        });
        setLastUpdated(new Date());
      }
    });

    // Live Firebase listener for alerts
    const alertsQuery = query(
      collection(db, "alerts"),
      orderBy("timestamp", "desc"),
      limit(10)
    );
    
    const unsubscribeAlerts = onSnapshot(alertsQuery, (snapshot) => {
      const alertsData = snapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data(),
        timestamp: doc.data().timestamp?.toDate?.() || new Date(doc.data().timestamp)
      }));
      setAlerts(alertsData);
    });

    // Auto refresh stats
    let interval;
    if (autoRefresh) {
      interval = setInterval(fetchStats, refreshInterval * 1000);
    }

    return () => {
      clearInterval(interval);
      unsubscribeReadings();
      unsubscribeAlerts();
    };
  }, [autoRefresh, refreshInterval]);

  const fetchStats = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/dashboard/stats', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats');
    }
  };

  const fetchLiveReadings = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/firebase/live', {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.data.length > 0) {
        const latest = response.data[0];
        setCurrentParams({
          ph: latest.ph || 7.2,
          temperature: latest.temperature || 22.5,
          do: latest.do || 8.1,
          turbidity: latest.turbidity || 2.3
        });
      }
      setLiveReadings(response.data);
    } catch (error) {
      console.error('Failed to fetch live readings');
    }
  };

  const fetchAlerts = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/firebase/alerts', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAlerts(response.data);
    } catch (error) {
      console.error('Failed to fetch alerts');
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    setIsAuthenticated(false);
    toast.success('Logged out successfully');
    navigate('/login');
  };

  // Prepare chart data
  const chartData = liveReadings.slice(0, 30).reverse().map((item, index) => ({
    time: item.timestamp ? new Date(item.timestamp).toLocaleTimeString() : `${index}m ago`,
    dwsi: item.dwsi || 70 + Math.random() * 20,
    ph: item.ph || 7.2,
    temperature: item.temperature || 22.5,
    do: item.do || 8.1,
    turbidity: item.turbidity || 2.3
  }));

  // Get trend icon for parameter
  const getTrendIcon = (value, normalMin, normalMax) => {
    if (value < normalMin) return <FaArrowDown className="text-red-400 text-xs" />;
    if (value > normalMax) return <FaArrowUp className="text-red-400 text-xs" />;
    return <FaMinus className="text-green-400 text-xs" />;
  };

  // Get status color for parameter
  const getStatusColor = (value, normalMin, normalMax) => {
    if (value < normalMin || value > normalMax) return "text-red-400";
    return "text-green-400";
  };

  // Parameter cards data
  const parameterCards = [
    { 
      label: "pH", 
      value: currentParams.ph, 
      unit: "", 
      icon: <FaFlask className="text-purple-400" />,
      normalMin: 6.5, 
      normalMax: 8.5,
      description: "Acidity/Alkalinity"
    },
    { 
      label: "Temperature", 
      value: currentParams.temperature, 
      unit: "°C", 
      icon: <FaThermometerHalf className="text-orange-400" />,
      normalMin: 15, 
      normalMax: 30,
      description: "Water temp"
    },
    { 
      label: "Dissolved O₂", 
      value: currentParams.do, 
      unit: "mg/L", 
      icon: <FaTachometerAlt className="text-blue-400" />,
      normalMin: 6, 
      normalMax: 12,
      description: "Oxygen level"
    },
    { 
      label: "Turbidity", 
      value: currentParams.turbidity, 
      unit: "NTU", 
      icon: <FaWater className="text-cyan-400" />,
      normalMin: 0, 
      normalMax: 5,
      description: "Cloudiness"
    }
  ];

  return (
    <div className="min-h-screen">
      {/* Sidebar */}
      <div className="fixed left-0 top-0 h-full w-64 glass border-r border-gray-800 z-20">
        <div className="p-6">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
              <FaTint className="text-white text-xl" />
            </div>
            <div>
              <h2 className="text-white font-bold">AquaWatch</h2>
              <p className="text-gray-400 text-xs">Water Quality Monitor</p>
            </div>
          </div>

          <nav className="space-y-2">
            <Link to="/dashboard/upload" className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-300 hover:bg-gray-800 transition">
              <FaUpload /> Upload Data
            </Link>
            <Link to="/dashboard/results" className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-300 hover:bg-gray-800 transition">
              <FaChartLine /> Results
            </Link>
            <Link to="/dashboard/history" className="flex items-center gap-3 px-4 py-3 rounded-lg text-gray-300 hover:bg-gray-800 transition">
              <FaHistory /> History
            </Link>
          </nav>

          <div className="absolute bottom-6 left-6 right-6">
            <div className="mb-4 p-3 bg-gray-800/50 rounded-lg">
              <div className="text-white text-sm font-medium">{user?.name}</div>
              <div className="text-gray-400 text-xs">{user?.email}</div>
            </div>
            <button
              onClick={handleLogout}
              className="flex items-center gap-3 px-4 py-3 w-full rounded-lg text-gray-300 hover:bg-red-500/20 hover:text-red-400 transition"
            >
              <FaSignOutAlt /> Logout
            </button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="ml-64 p-6">
        {/* 🔴 LIVE STATUS BAR */}
        <div className="bg-gray-800/50 rounded-xl p-3 mb-6 flex justify-between items-center border-l-4 border-green-500">
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            </div>
            <span className="text-green-400 font-semibold">LIVE</span>
            <span className="text-gray-400 text-sm">
              Last updated {Math.floor((new Date() - lastUpdated) / 1000)}s ago
            </span>
          </div>
          <div className="flex items-center gap-2">
            <FaClock className="text-gray-400 text-sm" />
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(parseInt(e.target.value))}
              className="bg-transparent text-white text-sm outline-none border border-gray-700 rounded px-2 py-1"
            >
              <option value={3}>3s</option>
              <option value={5}>5s</option>
              <option value={10}>10s</option>
              <option value={30}>30s</option>
            </select>
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`p-2 rounded transition ${autoRefresh ? 'text-blue-500 bg-blue-500/20' : 'text-gray-400'}`}
            >
              <FaSync className={autoRefresh ? 'animate-spin' : ''} style={{ animationDuration: '2s' }} />
            </button>
          </div>
        </div>

        {/* 📈 Live DWSI Trend Chart - MOST IMPORTANT VISUAL */}
        <div className="glass rounded-xl p-6 mb-6">
          <div className="flex justify-between items-center mb-4">
            <div>
              <h2 className="text-xl font-bold text-white">Live DWSI Trend</h2>
              <p className="text-gray-400 text-sm">Dynamic Water Quality Index - Higher is better</p>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-blue-400">
                {chartData.length > 0 ? chartData[chartData.length - 1]?.dwsi?.toFixed(1) : '72.4'}
              </div>
              <div className="text-gray-400 text-xs">Current DWSI</div>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={350}>
            <AreaChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="time" stroke="#94a3b8" fontSize={12} />
              <YAxis stroke="#94a3b8" fontSize={12} domain={[0, 100]} />
              <Tooltip 
                contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px' }}
                labelStyle={{ color: '#94a3b8' }}
              />
              <Area 
                type="monotone" 
                dataKey="dwsi" 
                stroke="#3b82f6" 
                strokeWidth={2}
                fill="url(#dwsiGradient)"
              />
              <defs>
                <linearGradient id="dwsiGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
            </AreaChart>
          </ResponsiveContainer>
          
          {/* Threshold indicators */}
          <div className="flex justify-between mt-4 text-xs text-gray-500">
            <span>⚠️ Critical (0-20)</span>
            <span>🔴 Poor (20-40)</span>
            <span>🟡 Moderate (40-60)</span>
            <span>🟢 Good (60-80)</span>
            <span>✅ Excellent (80-100)</span>
          </div>
        </div>

        {/* Two Column Layout: Parameter Cards + Alerts Panel */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
          {/* Parameter Cards - 4 cards in 2x2 grid */}
          <div className="lg:col-span-2">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {parameterCards.map((param, idx) => (
                <div key={idx} className="glass rounded-xl p-5 hover:bg-gray-800/40 transition">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2">
                      <div className="w-8 h-8 bg-gray-800 rounded-lg flex items-center justify-center">
                        {param.icon}
                      </div>
                      <span className="text-gray-300 font-medium">{param.label}</span>
                    </div>
                    {getTrendIcon(param.value, param.normalMin, param.normalMax)}
                  </div>
                  <div className="text-3xl font-bold text-white mb-1">
                    {param.value} {param.unit}
                  </div>
                  <div className="flex justify-between items-center">
                    <span className={`text-xs ${getStatusColor(param.value, param.normalMin, param.normalMax)}`}>
                      {param.value >= param.normalMin && param.value <= param.normalMax ? 'Normal' : 'Alert'}
                    </span>
                    <span className="text-gray-500 text-xs">
                      Range: {param.normalMin} - {param.normalMax} {param.unit}
                    </span>
                  </div>
                  {/* Progress bar */}
                  <div className="mt-3 w-full bg-gray-700 rounded-full h-1.5">
                    <div 
                      className={`h-1.5 rounded-full transition-all ${
                        param.value >= param.normalMin && param.value <= param.normalMax ? 'bg-green-500' : 'bg-red-500'
                      }`}
                      style={{ 
                        width: `${Math.min(100, ((param.value - param.normalMin) / (param.normalMax - param.normalMin)) * 100)}%` 
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* RIGHT SIDE - Alerts Panel */}
          <div className="glass rounded-xl p-5">
            <div className="flex items-center gap-2 mb-4 border-b border-gray-700 pb-3">
              <FaBell className="text-yellow-400" />
              <h3 className="text-white font-semibold">Live Alerts</h3>
              {alerts.length > 0 && (
                <span className="bg-red-500/20 text-red-400 text-xs px-2 py-0.5 rounded-full ml-2">
                  {alerts.length} new
                </span>
              )}
            </div>
            <div className="space-y-3 max-h-[320px] overflow-y-auto pr-1">
              {alerts.length === 0 ? (
                <div className="text-center py-8">
                  <FaCheckCircle className="text-green-500 text-4xl mx-auto mb-2" />
                  <p className="text-gray-400 text-sm">No active alerts</p>
                  <p className="text-gray-500 text-xs mt-1">All parameters normal</p>
                </div>
              ) : (
                alerts.map((alert, idx) => (
                  <div key={idx} className="bg-gray-800/50 rounded-lg p-3 border-l-2 border-red-500">
                    <div className="flex items-start gap-2">
                      <FaExclamationTriangle className="text-red-400 text-sm mt-0.5" />
                      <div className="flex-1">
                        <p className="text-white text-sm font-medium">{alert.message || alert.title}</p>
                        <p className="text-gray-400 text-xs mt-1">
                          {alert.location || alert.source || 'Unknown location'}
                        </p>
                        <p className="text-gray-500 text-xs mt-1">
                          {alert.timestamp ? new Date(alert.timestamp).toLocaleTimeString() : 'Just now'}
                        </p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* BOTTOM - Recent Readings Table */}
        <div className="glass rounded-xl p-5">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-white font-semibold">Recent Readings</h3>
            <div className="text-gray-400 text-xs">Last 20 records</div>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-700">
                  <th className="text-left py-3 text-gray-400 font-medium">Time</th>
                  <th className="text-left py-3 text-gray-400 font-medium">pH</th>
                  <th className="text-left py-3 text-gray-400 font-medium">Temp</th>
                  <th className="text-left py-3 text-gray-400 font-medium">DO</th>
                  <th className="text-left py-3 text-gray-400 font-medium">Turbidity</th>
                  <th className="text-left py-3 text-gray-400 font-medium">DWSI</th>
                  <th className="text-left py-3 text-gray-400 font-medium">Status</th>
                </tr>
              </thead>
              <tbody>
                {liveReadings.slice(0, 10).map((reading, idx) => (
                  <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/30 transition">
                    <td className="py-3 text-gray-300 text-xs">
                      {reading.timestamp ? new Date(reading.timestamp).toLocaleTimeString() : '-'}
                    </td>
                    <td className={`py-3 ${getStatusColor(reading.ph, 6.5, 8.5)}`}>
                      {reading.ph?.toFixed(1) || '-'}
                    </td>
                    <td className={`py-3 ${getStatusColor(reading.temperature, 15, 30)}`}>
                      {reading.temperature?.toFixed(1) || '-'}°C
                    </td>
                    <td className={`py-3 ${getStatusColor(reading.do, 6, 12)}`}>
                      {reading.do?.toFixed(1) || '-'} mg/L
                    </td>
                    <td className={`py-3 ${getStatusColor(reading.turbidity, 0, 5)}`}>
                      {reading.turbidity?.toFixed(1) || '-'} NTU
                    </td>
                    <td className="py-3 text-blue-400 font-medium">
                      {reading.dwsi?.toFixed(1) || '-'}
                    </td>
                    <td className="py-3">
                      {reading.dwsi >= 80 ? (
                        <span className="text-green-400 text-xs">✅ Excellent</span>
                      ) : reading.dwsi >= 60 ? (
                        <span className="text-blue-400 text-xs">👍 Good</span>
                      ) : reading.dwsi >= 40 ? (
                        <span className="text-yellow-400 text-xs">⚠️ Moderate</span>
                      ) : (
                        <span className="text-red-400 text-xs">🔴 Critical</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Routes for other pages */}
        <Routes>
          <Route path="/upload" element={<DataUpload />} />
          <Route path="/results" element={<Results />} />
          <Route path="/history" element={<HistoryView />} />
          <Route path="/" element={<></>} />
        </Routes>
      </div>
    </div>
  );
};

const HistoryView = () => {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get('http://localhost:8000/api/history', {
        headers: { Authorization: `Bearer ${token}` }
      });
      setHistory(response.data);
    } catch (error) {
      console.error('Failed to fetch history');
    }
  };

  return (
    <div className="glass rounded-xl p-6 mt-6">
      <h2 className="text-xl font-bold text-white mb-4">Analysis History</h2>
      <div className="space-y-3">
        {history.map((item) => (
          <div key={item.id} className="bg-gray-800/50 rounded-lg p-4 flex justify-between items-center">
            <div>
              <div className="text-white font-medium">{item.filename}</div>
              <div className="text-gray-400 text-sm">{new Date(item.uploaded_at).toLocaleString()}</div>
            </div>
            <div className="text-right">
              <div className="text-white">{item.total_records} records</div>
              <div className="text-yellow-400 text-sm">{item.anomalies} anomalies</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;