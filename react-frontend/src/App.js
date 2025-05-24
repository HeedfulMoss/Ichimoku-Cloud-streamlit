import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const API_BASE_URL = window.location.port === '30002' ? 'http://localhost:30000' : 'http://localhost:8000';

function App() {
  // State for inputs
  const [ticker, setTicker] = useState('AAPL');
  const [conversionLen, setConversionLen] = useState(9);
  const [baseLen, setBaseLen] = useState(26);
  const [laggingLen, setLaggingLen] = useState(26);
  const [leadingSpanBLen, setLeadingSpanBLen] = useState(52);
  const [cloudShift, setCloudShift] = useState(26);
  
  // Data source options
  const [useCsv, setUseCsv] = useState(true);
  const [useS3, setUseS3] = useState(false);
  const [useCache, setUseCache] = useState(true);
  
  // Lambda collection
  const [collectTicker, setCollectTicker] = useState('');
  const [lambdaStatus, setLambdaStatus] = useState({ show: false, message: '', type: 'info' });
  const [availableTickers, setAvailableTickers] = useState([]);
  
  // Status states
  const [status, setStatus] = useState('Ready');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(false);
  const [awsStatus, setAwsStatus] = useState({});
  const [dataSourceInfo, setDataSourceInfo] = useState(null);
  
  // Chart references
  const chartContainerRef = useRef(null);
  const volumeContainerRef = useRef(null);
  const chartRef = useRef(null);
  const volumeChartRef = useRef(null);
  const seriesRefs = useRef({});
  const LightweightChartsRef = useRef(null);
  
  // Check AWS status on mount
  useEffect(() => {
    checkAWSStatus();
    
    // Load lightweight-charts library
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js';
    script.async = true;
    script.onload = () => {
      LightweightChartsRef.current = window.LightweightCharts;
      initCharts();
      fetchAndDisplayData();
    };
    document.body.appendChild(script);
    
    return () => {
      document.body.removeChild(script);
      if (chartRef.current) chartRef.current.remove();
      if (volumeChartRef.current) volumeChartRef.current.remove();
    };
  }, []);
  
  const checkAWSStatus = async () => {
    try {
      setStatus('Checking AWS status...', true);
      const response = await fetch(`${API_BASE_URL}/aws/status`);
      const status = await response.json();
      setAwsStatus(status);
      
      // Check Lambda status
      const lambdaResponse = await fetch(`${API_BASE_URL}/aws/lambda/status`);
      const lambdaStatusData = await lambdaResponse.json();
      setAwsStatus(prev => ({ ...prev, ...lambdaStatusData }));
      
      // List available tickers
      if (status.s3_connected) {
        listAvailableTickers();
      }
    } catch (error) {
      console.error('Error checking AWS status:', error);
      setAwsStatus({ s3_connected: false, lambda_enabled: false });
    }
  };
  
  const listAvailableTickers = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/aws/tickers`);
      const result = await response.json();
      setAvailableTickers(result.tickers || []);
    } catch (error) {
      console.error('Error listing tickers:', error);
    }
  };
  
  const collectTickerData = async () => {
    const tickerToCollect = collectTicker.trim().toUpperCase();
    
    if (!tickerToCollect) {
      updateLambdaStatus('Please enter a ticker symbol', true);
      return;
    }
    
    updateLambdaStatus(`Collecting data for ${tickerToCollect}...`, false, 'info');
    
    try {
      const response = await fetch(`${API_BASE_URL}/aws/collect/${tickerToCollect}`, {
        method: 'POST'
      });
      
      if (response.ok) {
        const result = await response.json();
        const message = result.data_existed 
          ? `✅ Updated data for ${tickerToCollect} (${result.rows_processed} rows)`
          : `✅ Collected ${result.rows_processed} rows for ${tickerToCollect}`;
        updateLambdaStatus(message, false, 'success');
        setCollectTicker('');
        setTimeout(listAvailableTickers, 1000);
      } else {
        const error = await response.json();
        updateLambdaStatus(`❌ Error: ${error.detail}`, true);
      }
    } catch (error) {
      updateLambdaStatus(`❌ Network error: ${error.message}`, true);
    }
  };
  
  const updateLambdaStatus = (message, isError = false, type = 'info') => {
    setLambdaStatus({ show: true, message, type: isError ? 'error' : type });
    
    if (!isError) {
      setTimeout(() => {
        setLambdaStatus(prev => prev.message === message ? { ...prev, show: false } : prev);
      }, 5000);
    }
  };
  
  const updateStatus = (message, loading = false, error = false) => {
    setStatus(message);
    setLoading(loading);
    setError(error);
  };
  
  const initCharts = () => {
    if (!LightweightChartsRef.current || !chartContainerRef.current || !volumeContainerRef.current) {
      return false;
    }
    
    try {
      // Clear previous charts
      if (chartRef.current) chartRef.current.remove();
      if (volumeChartRef.current) volumeChartRef.current.remove();
      
      // Create main chart
      chartRef.current = LightweightChartsRef.current.createChart(chartContainerRef.current, {
        width: chartContainerRef.current.clientWidth,
        height: 500,
        layout: {
          background: { type: 'solid', color: 'white' },
          textColor: '#333',
        },
        grid: {
          vertLines: { color: 'rgba(197, 203, 206, 0.5)' },
          horzLines: { color: 'rgba(197, 203, 206, 0.5)' }
        },
        crosshair: {
          mode: LightweightChartsRef.current.CrosshairMode.Normal,
        },
        rightPriceScale: {
          borderColor: 'rgba(197, 203, 206, 0.8)',
        },
        timeScale: {
          borderColor: 'rgba(197, 203, 206, 0.8)',
          timeVisible: true,
          rightOffset: 30,
          barSpacing: 15,
        },
      });
      
      // Create volume chart
      volumeChartRef.current = LightweightChartsRef.current.createChart(volumeContainerRef.current, {
        width: volumeContainerRef.current.clientWidth,
        height: 150,
        layout: {
          background: { type: 'solid', color: 'white' },
          textColor: '#333',
        },
        grid: {
          vertLines: { color: 'rgba(197, 203, 206, 0.5)' },
          horzLines: { color: 'rgba(197, 203, 206, 0.5)' }
        },
        rightPriceScale: {
          scaleMargins: { top: 0.1, bottom: 0.1 },
        },
        timeScale: {
          borderColor: 'rgba(197, 203, 206, 0.8)',
          timeVisible: true,
          rightOffset: 30,
          barSpacing: 15,
        },
      });
      
      // Sync time scales
      chartRef.current.timeScale().subscribeVisibleTimeRangeChange(timeRange => {
        if (timeRange && volumeChartRef.current) {
          volumeChartRef.current.timeScale().setVisibleRange(timeRange);
        }
      });
      
      // Create series
      seriesRefs.current.candleSeries = chartRef.current.addCandlestickSeries({
        upColor: 'rgba(38, 166, 154, 0.9)',
        downColor: 'rgba(239, 83, 80, 0.9)',
        borderVisible: false,
        wickUpColor: 'rgba(38, 166, 154, 0.9)',
        wickDownColor: 'rgba(239, 83, 80, 0.9)',
      });
      
      seriesRefs.current.volumeSeries = volumeChartRef.current.addHistogramSeries({
        color: '#26a69a',
        priceFormat: { type: 'volume' },
      });
      
      // Create Ichimoku series
      seriesRefs.current.tenkanSeries = chartRef.current.addLineSeries({
        color: 'blue',
        lineWidth: 2,
        title: 'Conversion Line (Tenkan-sen)',
      });
      
      seriesRefs.current.kijunSeries = chartRef.current.addLineSeries({
        color: 'orange',
        lineWidth: 2,
        title: 'Base Line (Kijun-sen)',
      });
      
      seriesRefs.current.chikouSeries = chartRef.current.addLineSeries({
        color: 'purple',
        lineWidth: 1,
        title: 'Lagging Span (Chikou Span)',
      });
      
      seriesRefs.current.senkouASeries = chartRef.current.addLineSeries({
        color: 'green',
        lineWidth: 1,
        lineStyle: LightweightChartsRef.current.LineStyle.Dashed,
        title: 'Leading Span A',
      });
      
      seriesRefs.current.senkouBSeries = chartRef.current.addLineSeries({
        color: 'red',
        lineWidth: 1,
        lineStyle: LightweightChartsRef.current.LineStyle.Dashed,
        title: 'Leading Span B',
      });
      
      // Create cloud area series
      seriesRefs.current.bullishCloudSeries = chartRef.current.addAreaSeries({
        topColor: 'rgba(0, 255, 0, 0.3)',
        bottomColor: 'rgba(0, 255, 0, 0.1)',
        lineColor: 'transparent',
        lineWidth: 0,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      
      seriesRefs.current.bearishCloudSeries = chartRef.current.addAreaSeries({
        topColor: 'rgba(255, 0, 0, 0.3)',
        bottomColor: 'rgba(255, 0, 0, 0.1)',
        lineColor: 'transparent',
        lineWidth: 0,
        crosshairMarkerVisible: false,
        lastValueVisible: false,
        priceLineVisible: false,
      });
      
      // Handle resize
      const handleResize = () => {
        if (chartRef.current && chartContainerRef.current) {
          chartRef.current.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
        if (volumeChartRef.current && volumeContainerRef.current) {
          volumeChartRef.current.applyOptions({ width: volumeContainerRef.current.clientWidth });
        }
      };
      
      window.addEventListener('resize', handleResize);
      
      return true;
    } catch (error) {
      console.error('Error initializing charts:', error);
      updateStatus(`Error initializing charts: ${error.message}`, false, true);
      return false;
    }
  };
  
  const fetchAndDisplayData = async () => {
    const tickerUpper = ticker.trim().toUpperCase();
    
    if (!tickerUpper) {
      updateStatus('Please enter a ticker symbol', false, true);
      return;
    }
    
    updateStatus(`Fetching data for ${tickerUpper}...`, true);
    
    try {
      if (!chartRef.current || !volumeChartRef.current) {
        if (!initCharts()) {
          throw new Error('Failed to initialize charts');
        }
      }
      
      // Fetch raw data
      const params = new URLSearchParams();
      if (useCsv) params.append('use_csv', 'true');
      if (useS3) params.append('use_s3', 'true');
      if (useCache) params.append('use_cache', 'true');
      
      const url = `${API_BASE_URL}/data/${tickerUpper}${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url);
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status} error`);
      }
      
      const rawData = await response.json();
      
      if (!rawData || !rawData.data || !Array.isArray(rawData.data) || rawData.data.length === 0) {
        throw new Error('No data available');
      }
      
      setDataSourceInfo(rawData);
      
      updateStatus(`Calculating Ichimoku indicators for ${tickerUpper}...`, true);
      
      // Calculate Ichimoku
      const ichimokuRequest = {
        data: rawData.data,
        conversion_len: conversionLen,
        base_len: baseLen,
        lagging_len: laggingLen,
        leading_span_b_len: leadingSpanBLen,
        cloud_shift: cloudShift
      };
      
      const ichimokuResponse = await fetch(`${API_BASE_URL}/ichimoku`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(ichimokuRequest)
      });
      
      if (!ichimokuResponse.ok) {
        const errorData = await ichimokuResponse.json();
        throw new Error(`Ichimoku calculation failed: ${errorData.detail || 'Unknown error'}`);
      }
      
      const ichimokuData = await ichimokuResponse.json();
      
      updateStatus(`Rendering chart for ${tickerUpper}...`, true);
      
      // Update chart data
      updateChartData(ichimokuData.data);
      
      const sourceDisplay = {
        's3_cache': 'AWS S3 cache',
        's3_csv': 'AWS S3 CSV',
        'local_csv': 'local CSV backup',
        'yahoo_finance': 'Yahoo Finance'
      };
      
      const dataSource = sourceDisplay[rawData.source] || rawData.source;
      updateStatus(`Successfully loaded Ichimoku chart for ${tickerUpper} from ${dataSource}`);
      
    } catch (error) {
      console.error('Error:', error);
      updateStatus(`Error: ${error.message}`, false, true);
      setDataSourceInfo(null);
    }
  };
  
  const updateChartData = (data) => {
    // Format candlestick data
    const candleData = data.filter(item => 
      item.time && item.open !== null && item.high !== null && 
      item.low !== null && item.close !== null
    ).map(item => ({
      time: item.time,
      open: item.open,
      high: item.high,
      low: item.low,
      close: item.close
    }));
    
    // Format volume data
    const volumeData = data.filter(item => 
      item.time && item.volume !== null
    ).map(item => ({
      time: item.time,
      value: item.volume,
      color: item.close > item.open ? 'rgba(38, 166, 154, 0.9)' : 'rgba(239, 83, 80, 0.9)'
    }));
    
    // Format line data
    const formatLineData = (data, field) => {
      return data.filter(item => 
        item.time && item[field] !== null && item[field] !== undefined && !isNaN(item[field])
      ).map(item => ({
        time: item.time,
        value: item[field]
      }));
    };
    
    // Create cloud data
    const bullishData = [];
    const bearishData = [];
    
    for (const item of data) {
      if (item.senkou_span_a !== null && item.senkou_span_b !== null && 
          !isNaN(item.senkou_span_a) && !isNaN(item.senkou_span_b)) {
        
        if (item.senkou_span_a >= item.senkou_span_b) {
          bullishData.push({
            time: item.time,
            value: Math.max(item.senkou_span_a, item.senkou_span_b)
          });
          bearishData.push({
            time: item.time,
            value: Math.min(item.senkou_span_a, item.senkou_span_b)
          });
        } else {
          bearishData.push({
            time: item.time,
            value: Math.max(item.senkou_span_a, item.senkou_span_b)
          });
          bullishData.push({
            time: item.time,
            value: Math.min(item.senkou_span_a, item.senkou_span_b)
          });
        }
      }
    }
    
    // Set all data
    seriesRefs.current.candleSeries.setData(candleData);
    seriesRefs.current.volumeSeries.setData(volumeData);
    seriesRefs.current.tenkanSeries.setData(formatLineData(data, 'tenkan_sen'));
    seriesRefs.current.kijunSeries.setData(formatLineData(data, 'kijun_sen'));
    seriesRefs.current.chikouSeries.setData(formatLineData(data, 'chikou_span'));
    seriesRefs.current.senkouASeries.setData(formatLineData(data, 'senkou_span_a'));
    seriesRefs.current.senkouBSeries.setData(formatLineData(data, 'senkou_span_b'));
    seriesRefs.current.bullishCloudSeries.setData(bullishData);
    seriesRefs.current.bearishCloudSeries.setData(bearishData);
    
    // Fit content
    chartRef.current.timeScale().fitContent();
    volumeChartRef.current.timeScale().fitContent();
  };
  
  return (
    <div className="App">
      <div className="container">
        <h1>Ichimoku Cloud Chart</h1>
        
        <div className="controls">
          <div className="input-group">
            <label htmlFor="ticker">Ticker Symbol</label>
            <input
              type="text"
              id="ticker"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && fetchAndDisplayData()}
              placeholder="Enter ticker symbol"
            />
          </div>
          
          <div className="input-group">
            <label htmlFor="conversion-len">Conversion Line Length</label>
            <input
              type="number"
              id="conversion-len"
              value={conversionLen}
              onChange={(e) => setConversionLen(parseInt(e.target.value) || 9)}
              min="1"
            />
          </div>
          
          <div className="input-group">
            <label htmlFor="base-len">Base Line Length</label>
            <input
              type="number"
              id="base-len"
              value={baseLen}
              onChange={(e) => setBaseLen(parseInt(e.target.value) || 26)}
              min="1"
            />
          </div>
          
          <div className="input-group">
            <label htmlFor="lagging-len">Lagging Span Length</label>
            <input
              type="number"
              id="lagging-len"
              value={laggingLen}
              onChange={(e) => setLaggingLen(parseInt(e.target.value) || 26)}
              min="1"
            />
          </div>
          
          <div className="input-group">
            <label htmlFor="leading-span-b-len">Leading Span B Length</label>
            <input
              type="number"
              id="leading-span-b-len"
              value={leadingSpanBLen}
              onChange={(e) => setLeadingSpanBLen(parseInt(e.target.value) || 52)}
              min="1"
            />
          </div>
          
          <div className="input-group">
            <label htmlFor="cloud-shift">Cloud Shift</label>
            <input
              type="number"
              id="cloud-shift"
              value={cloudShift}
              onChange={(e) => setCloudShift(parseInt(e.target.value) || 26)}
              min="1"
            />
          </div>
          
          <button onClick={fetchAndDisplayData} disabled={loading}>
            Update Chart
          </button>
        </div>
        
        <div className="data-source-controls">
          <h4>Data Source Options</h4>
          <div className="checkbox-row">
            <div className="checkbox-group">
              <input
                type="checkbox"
                id="use-csv"
                checked={useCsv}
                onChange={(e) => setUseCsv(e.target.checked)}
              />
              <label htmlFor="use-csv">Use Local CSV Backup</label>
            </div>
            <div className="checkbox-group">
              <input
                type="checkbox"
                id="use-s3"
                checked={useS3}
                onChange={(e) => setUseS3(e.target.checked)}
                disabled={!awsStatus.s3_connected}
              />
              <label htmlFor="use-s3">Use AWS S3 Data</label>
            </div>
            <div className="checkbox-group">
              <input
                type="checkbox"
                id="use-cache"
                checked={useCache}
                onChange={(e) => setUseCache(e.target.checked)}
              />
              <label htmlFor="use-cache">Use S3 Cache</label>
            </div>
          </div>
        </div>
        
        {awsStatus.s3_connected && (
          <div className="lambda-controls">
            <h4>🚀 Data Collection (AWS Lambda)</h4>
            <div className="lambda-input-row">
              <div className="input-group" style={{ margin: 0 }}>
                <label htmlFor="collect-ticker">Ticker to Collect</label>
                <input
                  type="text"
                  id="collect-ticker"
                  value={collectTicker}
                  onChange={(e) => setCollectTicker(e.target.value)}
                  onKeyPress={(e) => e.key === 'Enter' && collectTickerData()}
                  placeholder="e.g., MSFT, GOOGL"
                />
              </div>
              <button
                className="collect"
                onClick={collectTickerData}
                disabled={!awsStatus.lambda_enabled || !collectTicker.trim()}
              >
                Collect Data
              </button>
              <button
                className="secondary"
                onClick={listAvailableTickers}
              >
                Refresh List
              </button>
            </div>
            
            {lambdaStatus.show && (
              <div className={`lambda-status ${lambdaStatus.type}`}>
                {lambdaStatus.message}
              </div>
            )}
            
            {availableTickers.length > 0 && (
              <div className="available-tickers">
                <strong>Available in S3:</strong>
                <span className="ticker-list">{availableTickers.join(', ')}</span>
              </div>
            )}
          </div>
        )}
        
        {useS3 && !awsStatus.s3_connected && (
          <div className="warning">
            ⚠️ AWS S3 is not connected. S3 options will be ignored.
          </div>
        )}
        
        {awsStatus.s3_connected !== undefined && (
          <div className={`aws-status-info ${awsStatus.s3_connected ? 'aws-connected' : 'aws-error'}`}>
            <strong>AWS Status:</strong>{' '}
            {awsStatus.s3_connected
              ? `✅ S3 Connected (${awsStatus.bucket_name})`
              : '❌ AWS not available'}
          </div>
        )}
        
        {dataSourceInfo && (
          <div className={`data-source-info ${
            dataSourceInfo.source?.startsWith('s3_') ? 's3-mode' : 
            dataSourceInfo.source === 'local_csv' ? 'csv-mode' : ''
          }`}>
            <strong>Data Source:</strong> {
              {
                's3_cache': 'AWS S3 Cache',
                's3_csv': 'AWS S3 CSV',
                'local_csv': 'Local CSV',
                'yahoo_finance': 'Yahoo Finance'
              }[dataSourceInfo.source] || dataSourceInfo.source
            } | 
            <strong> Ticker:</strong> {dataSourceInfo.ticker} | 
            <strong> Data Points:</strong> {dataSourceInfo.count}
          </div>
        )}
        
        <div className="legend">
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: 'blue' }}></span>
            Conversion Line (Tenkan-sen)
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: 'orange' }}></span>
            Base Line (Kijun-sen)
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: 'purple' }}></span>
            Lagging Span (Chikou Span)
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: 'green' }}></span>
            Leading Span A
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: 'red' }}></span>
            Leading Span B
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: 'rgba(0,255,0,0.3)' }}></span>
            Bullish Cloud
          </div>
          <div className="legend-item">
            <span className="legend-color" style={{ backgroundColor: 'rgba(255,0,0,0.3)' }}></span>
            Bearish Cloud
          </div>
        </div>
        
        <div id="chart-container" ref={chartContainerRef}></div>
        <div id="volume-container" ref={volumeContainerRef}></div>
        
        <div className={`status ${error ? 'error' : ''}`}>
          {status}
        </div>
      </div>
    </div>
  );
}

export default App;