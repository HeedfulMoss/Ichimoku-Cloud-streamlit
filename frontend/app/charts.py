import json
from streamlit_lightweight_charts import renderLightweightCharts
import numpy as np
import streamlit as st
#from lightweightcharts import LineSeries, AreaSeries, Indicator

# Define color constants for candlesticks, volume, lines, etc.
COLOR_BULL = 'rgba(38,166,154,0.9)' # #26a69a
COLOR_BEAR = 'rgba(239,83,80,0.9)'  # #ef5350
LIGHT_GREEN = 'rgba(144,238,144,0.3)'
LIGHT_RED   = 'rgba(255,182,193,0.3)'

def render_chart(df, df_ichimoku, ticker_name):
    """
    Render a multi-pane chart (candles + volume + Ichimoku Cloud) using
    streamlit_lightweight_charts.
    """
    try:
        # Check if we have enough data to render
        if len(df) == 0:
            st.error("No data available to render chart")
            return
            
        # Convert candle data to JSON
        candles = json.loads(
            df[['time','open','high','low','close']]
              .assign(color = np.where(df['open'] > df['close'], COLOR_BEAR, COLOR_BULL))
              .to_json(orient="records")
        )

        # 2) Convert volume data to JSON, but also assign color on a per-bar basis.
        #    If today's close is higher than today's open => green volume, else red.
        df_volume = df[['time','open','close','volume']].copy()
        df_volume = df_volume.rename(columns={"volume": "value"})
        df_volume['color'] = np.where(df_volume['close'] > df_volume['open'], COLOR_BULL, COLOR_BEAR)
        volume = json.loads(df_volume.to_json(orient="records"))

        # Ichimoku JSON: Tenkan, Kijun, Chikou, Senkou A, Senkou B
        tenkan_sen = json.loads(
            df_ichimoku[['time','tenkan_sen']]
              .rename(columns={"tenkan_sen": "value"})
              .dropna()
              .to_json(orient="records")
        )
        kijun_sen = json.loads(
            df_ichimoku[['time','kijun_sen']]
              .rename(columns={"kijun_sen": "value"})
              .dropna()
              .to_json(orient="records")
        )
        chikou_span = json.loads(
            df_ichimoku[['time','chikou_span']]
              .rename(columns={"chikou_span": "value"})
              .dropna()
              .to_json(orient="records")
        )
        senkou_span_a = json.loads(
            df_ichimoku[['time','senkou_span_a']]
              .rename(columns={"senkou_span_a": "value"})
              .dropna()
              .to_json(orient="records")
        )
        senkou_span_b = json.loads(
            df_ichimoku[['time','senkou_span_b']]
              .rename(columns={"senkou_span_b": "value"})
              .dropna()
              .to_json(orient="records")
        )

        # 1) Build the partial arrays
        cloud_bullish_top, cloud_bullish_bottom = [], []
        cloud_bearish_top, cloud_bearish_bottom = [], []

        for a_pt, b_pt in zip(senkou_span_a, senkou_span_b):
            if a_pt["time"] == b_pt["time"]:
                a_val = a_pt["value"]
                b_val = b_pt["value"]
                if (a_val is not None) and (b_val is not None):
                    if a_val >= b_val:
                        cloud_bullish_top.append({"time": a_pt["time"], "value": a_val})
                        cloud_bullish_bottom.append({"time": a_pt["time"], "value": b_val})
                        # No fill for bearish in this region
                        cloud_bearish_top.append({"time": a_pt["time"], "value": None})
                        cloud_bearish_bottom.append({"time": a_pt["time"], "value": None})
                    else:
                        cloud_bearish_top.append({"time": b_pt["time"], "value": b_val})
                        cloud_bearish_bottom.append({"time": b_pt["time"], "value": a_val})
                        # No fill for bullish in this region
                        cloud_bullish_top.append({"time": a_pt["time"], "value": None})
                        cloud_bullish_bottom.append({"time": a_pt["time"], "value": None})
                else:
                    # break the fill
                    cloud_bullish_top.append({"time": a_pt["time"], "value": None})
                    cloud_bullish_bottom.append({"time": a_pt["time"], "value": None})
                    cloud_bearish_top.append({"time": a_pt["time"], "value": None})
                    cloud_bearish_bottom.append({"time": a_pt["time"], "value": None})

        # 5) Chart config
        chartMultipaneOptions = [
            {
                "width": 600,
                "height": 400,
                "layout": {
                    "background": {"type": "solid", "color": "white"},
                    "textColor": "black"
                },
                "grid": {
                    "vertLines": {"color": "rgba(197, 203, 206, 0.5)"},
                    "horzLines": {"color": "rgba(197, 203, 206, 0.5)"}
                },
                "crosshair": {"mode": 0},
                "priceScale": {"borderColor": "rgba(197, 203, 206, 0.8)"},
                "timeScale": {
                    "borderColor": "rgba(197, 203, 206, 0.8)",
                    "barSpacing": 15,
                    # Increase offset so future-shifted cloud is visible
                    "rightOffset": 30  
                },
                "watermark": {
                    "visible": True,
                    "fontSize": 48,
                    "horzAlign": "center",
                    "vertAlign": "center",
                    "color": "rgba(171, 71, 188, 0.3)",
                    "text": ticker_name
                }
            },
            {
                "width": 600,
                "height": 100,
                "layout": {
                    "background": {"type": "solid", "color": "transparent"},
                    "textColor": "black"
                },
                "grid": {
                    "vertLines": {"color": "rgba(42, 46, 57, 0)"},
                    "horzLines": {"color": "rgba(42, 46, 57, 0.6)"}
                },
                "timeScale": {"visible": False},
                "watermark": {
                    "visible": True,
                    "fontSize": 18,
                    "horzAlign": "left",
                    "vertAlign": "top",
                    "color": "rgba(171, 71, 188, 0.7)",
                    "text": "Volume"
                }
            }
        ]

        # 6) Candlestick & volume series
        seriesCandlestickChart = [
            {
                "type": "Candlestick",
                "data": candles,
                "options": {
                    "upColor": COLOR_BULL,
                    "downColor": COLOR_BEAR,
                    "borderVisible": False,
                    "wickUpColor": COLOR_BULL,
                    "wickDownColor": COLOR_BEAR
                }
            }
        ]
        seriesVolumeChart = [
            {
                "type": "Histogram",
                "data": volume,
                "options": {
                    "priceFormat": {"type": "volume"},
                    "priceScaleId": ""
                },
                "priceScale": {
                    "scaleMargins": {"top": 0, "bottom": 0},
                    "alignLabels": False
                }
            }
        ]

        # 7) Ichimoku lines: A (green), B (red), Tenkan, Kijun, Chikou
        seriesIchimokuLines = [
            {"type": "Line", "data": senkou_span_a, "options": {"color": "green", "lineWidth": 1, "lineStyle": 2}},
            {"type": "Line", "data": senkou_span_b, "options": {"color": "red",   "lineWidth": 1, "lineStyle": 2}},
        ]
        seriesIchimokuMainLines = [
            {"type": "Line", "data": tenkan_sen,    "options": {"color": "blue",   "lineWidth": 1}},
            {"type": "Line", "data": kijun_sen,     "options": {"color": "orange", "lineWidth": 1}},
            {"type": "Line", "data": chikou_span,   "options": {"color": "black",  "lineWidth": 1}},
        ]

        # 2) Define the 4 "Area" series
        seriesBullishCloud = [
            {
                "type": "Area",
                "data": cloud_bullish_top,
                "options": {
                    "lineColor": "transparent",
                    "lineWidth": 0,
                    "topColor": "rgba(0,255,0,0.3)",
                    "bottomColor": "rgba(0,255,0,0.3)",
                },
                "stack": False
            },
            {
                "type": "Area",
                "data": cloud_bullish_bottom,
                "options": {
                    "lineColor": "transparent",
                    "lineWidth": 0,
                    "topColor": "rgba(0,255,0,0.0)",
                    "bottomColor": "rgba(0,255,0,0.0)",
                },
                "stack": True
            }
        ]

        seriesBearishCloud = [
            {
                "type": "Area",
                "data": cloud_bearish_top,
                "options": {
                    "lineColor": "transparent",
                    "lineWidth": 0,
                    "topColor": "rgba(255,0,0,0.3)",
                    "bottomColor": "rgba(255,0,0,0.3)",
                },
                "stack": False
            },
            {
                "type": "Area",
                "data": cloud_bearish_bottom,
                "options": {
                    "lineColor": "transparent",
                    "lineWidth": 0,
                    "topColor": "rgba(255,0,0,0.0)",
                    "bottomColor": "rgba(255,0,0,0.0)",
                },
                "stack": True
            }
        ]

        # 3) Add them to your final Ichimoku series, after you plot
        #    the lines for Senkou A/B, Tenkan, Kijun, etc.
        seriesIchimokuCloud = [
            # lines first
            *seriesIchimokuMainLines,
            *seriesIchimokuLines,
            # then the "four area" method:
            *seriesBullishCloud,
            *seriesBearishCloud
        ]

        # 9) Render the multi-pane chart
        try:
            renderLightweightCharts(
                [
                    {
                        "chart": chartMultipaneOptions[0],
                        "series": seriesCandlestickChart + seriesIchimokuCloud
                    },
                    {
                        "chart": chartMultipaneOptions[1],
                        "series": seriesVolumeChart
                    }
                ],
                "multipane"
            )
        except Exception as chart_error:
            st.error(f"Error rendering chart: {str(chart_error)}")
            # Fallback to a simple chart
            st.write("Showing a basic chart as fallback:")
            st.line_chart(df[['time', 'close']].set_index('time'))
            
    except json.JSONDecodeError as e:
        st.error(f"JSON decode error: {str(e)}")
        st.write("There was a problem processing the chart data")
        # Provide a simple fallback
        st.line_chart(df[['time', 'close']].set_index('time') if not df.empty else pd.DataFrame())
    except Exception as e:
        st.error(f"Error preparing chart data: {str(e)}")
        import traceback
        st.text(traceback.format_exc())