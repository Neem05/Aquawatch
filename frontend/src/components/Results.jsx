import React, { useState, useEffect } from 'react';
import axios from 'axios';
import toast from 'react-hot-toast';
import { FaDownload, FaChartBar, FaTable, FaCheckCircle, FaExclamationTriangle, FaInfoCircle } from 'react-icons/fa';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell
} from 'recharts';

const Results = () => {
  const [analysis, setAnalysis] = useState(null);
  const [view, setView] = useState('summary');
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    const data = localStorage.getItem('currentAnalysis');
    if (data) {
      setAnalysis(JSON.parse(data));
    }
  }, []);

  const handleExport = async () => {
    if (!analysis?.analysis_id) return;
    
    setExporting(true);
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`http://localhost:8000/api/results/export/${analysis.analysis_id}`, {
        headers: { Authorization: `Bearer ${token}` },
        responseType: 'blob'
      });
      
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `water_quality_report_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      
      toast.success('Report exported successfully');
    } catch (error) {
      toast.error('Export failed');
    } finally {
      setExporting(false);
    }
  };

  if (!analysis) {
    return (
      <div className="glass rounded-xl p-12 text-center">
        <FaInfoCircle className="text-6xl text-gray-500 mx-auto mb-4" />
        <p className="text-gray-400">No analysis results found</p>
        <p className="text-gray-500 text-sm mt-2">Please upload data first</p>
      </div>
    );
  }

  // Prepare chart data
  const chartData = analysis.results?.slice(0, 20).map((r, idx) => ({
    index: idx,
    dwsi: r.dwsi,
    ph: r.parameters?.ph?.value || 0,
    temperature: r.parameters?.temperature?.value || 0
  })) || [];

  const qualityDistribution = [
    { name: 'Excellent', value: analysis.results?.filter(r => r.dwsi >= 80).length || 0, color: '#00d4aa' },
    { name: 'Good', value: analysis.results?.filter(r => r.dwsi >= 60 && r.dwsi < 80).length || 0, color: '#3a9eff' },
    { name: 'Moderate', value: analysis.results?.filter(r => r.dwsi >= 40 && r.dwsi < 60).length || 0, color: '#f59e0b' },
    { name: 'Poor', value: analysis.results?.filter(r => r.dwsi >= 20 && r.dwsi < 40).length || 0, color: '#ef4444' },
    { name: 'Critical', value: analysis.results?.filter(r => r.dwsi < 20).length || 0, color: '#dc2626' }
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="glass rounded-xl p-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Analysis Results</h2>
            <p className="text-gray-400 mt-1">
              {analysis.total_records} records analyzed • {analysis.anomalies} anomalies detected
            </p>
          </div>
          <button
            onClick={handleExport}
            disabled={exporting}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 rounded-lg text-white hover:bg-green-700 transition"
          >
            <FaDownload /> {exporting ? 'Exporting...' : 'Export Report'}
          </button>
        </div>
        
        {/* Summary Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          <div className="bg-gray-800/50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-blue-400">{analysis.average_dwsi?.toFixed(1)}</div>
            <div className="text-gray-400 text-sm">Average DWSI</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-yellow-400">{analysis.anomalies}</div>
            <div className="text-gray-400 text-sm">Anomalies</div>
          </div>
          <div className="bg-gray-800/50 rounded-lg p-4 text-center">
            <div className="text-2xl font-bold text-green-400">
              {((analysis.total_records - analysis.anomalies) / analysis.total_records * 100).toFixed(1)}%
            </div>
            <div className="text-gray-400 text-sm">Compliance Rate</div>
          </div>
        </div>
      </div>

      {/* View Toggle */}
      <div className="flex gap-2">
        <button
          onClick={() => setView('summary')}
          className={`px-4 py-2 rounded-lg transition ${view === 'summary' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
        >
          <FaChartBar className="inline mr-2" /> Summary
        </button>
        <button
          onClick={() => setView('table')}
          className={`px-4 py-2 rounded-lg transition ${view === 'table' ? 'bg-blue-600 text-white' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
        >
          <FaTable className="inline mr-2" /> Data Table
        </button>
      </div>

      {view === 'summary' ? (
        <>
          {/* DWSI Trend Chart */}
          <div className="glass rounded-xl p-6">
            <h3 className="text-white font-semibold mb-4">DWSI Trend</h3>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="index" stroke="#94a3b8" />
                <YAxis stroke="#94a3b8" />
                <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none' }} />
                <Legend />
                <Line type="monotone" dataKey="dwsi" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Quality Distribution */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <div className="glass rounded-xl p-6">
              <h3 className="text-white font-semibold mb-4">Quality Distribution</h3>
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={qualityDistribution}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) =>
                      percent > 0
                        ? `${name} ${(percent * 100).toFixed(0)}%`
                        : ''
                    }
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {qualityDistribution.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>

            {/* Parameter Statistics */}
            <div className="glass rounded-xl p-6">
              <h3 className="text-white font-semibold mb-4">Parameter Statistics</h3>
              <div className="space-y-3">
                {analysis.results?.[0]?.parameters && Object.entries(analysis.results[0].parameters).map(([key, value]) => (
                  <div key={key}>
                    <div className="flex justify-between text-sm mb-1">
                      <span className="text-gray-400">{key.toUpperCase()}</span>
                      <span className="text-white">{value.value}</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-2">
                      <div
                        className="h-2 rounded-full"
                        style={{
                          width: `${Math.max(
                            0,
                            Math.min(
                              ((value.value - value.min) / (value.max - value.min)) * 100,
                              100
                            )
                          )}%`,
                          backgroundColor: value.normal ? '#10b981' : '#ef4444'
                        }}
                      />
                    </div>
                    <div className="text-xs text-gray-500 mt-1">Range: {value.min} - {value.max}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      ) : (
        // Data Table View
        <div className="glass rounded-xl p-6 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-700">
                <th className="text-left py-3 text-gray-400">#</th>
                <th className="text-left py-3 text-gray-400">DWSI</th>
                <th className="text-left py-3 text-gray-400">Quality</th>
                <th className="text-left py-3 text-gray-400">pH</th>
                <th className="text-left py-3 text-gray-400">Temp</th>
                <th className="text-left py-3 text-gray-400">DO</th>
                <th className="text-left py-3 text-gray-400">Turbidity</th>
                <th className="text-left py-3 text-gray-400">Salinity</th>
                <th className="text-left py-3 text-gray-400">Status</th>
              </tr>
            </thead>
            <tbody>
              {analysis.results?.map((result, idx) => (
                <tr key={idx} className="border-b border-gray-800 hover:bg-gray-800/30">
                  <td className="py-3 text-gray-400">{idx + 1}</td>
                  <td className="py-3 text-white font-medium">{result.dwsi}</td>
                  <td className="py-3">
                    <span className={`px-2 py-1 rounded-full text-xs ${
                      result.quality_status === 'safe' ? 'bg-green-500/20 text-green-400' :
                      result.quality_status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                      'bg-red-500/20 text-red-400'
                    }`}>
                      {result.quality_label}
                    </span>
                  </td>
                  <td className="py-3 text-gray-300">{result.parameters?.ph?.value}</td>
                  <td className="py-3 text-gray-300">{result.parameters?.temperature?.value}</td>
                  <td className="py-3 text-gray-300">{result.parameters?.do?.value}</td>
                  <td className="py-3 text-gray-300">{result.parameters?.turbidity?.value}</td>
                  <td className="py-3 text-gray-300">{result.parameters?.salinity?.value}</td>
                  <td className="py-3">
                    {result.is_anomaly ? (
                      <FaExclamationTriangle className="text-yellow-400" />
                    ) : (
                      <FaCheckCircle className="text-green-400" />
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};

export default Results;