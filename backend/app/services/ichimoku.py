import numpy as np
import pandas as pd
from datetime import timedelta, datetime

# Define any colors you may need here or in a config
LIGHT_GREEN = 'rgba(144,238,144,0.3)'
LIGHT_RED   = 'rgba(255,182,193,0.3)'

def apply_ichimoku_cloud(df_in,
                         conversion_len=9,
                         base_len=26,
                         lagging_len=26,
                         leading_span_b_len=52,
                         cloud_shift=26):
    """
    Calculate Ichimoku Cloud columns and return an extended DataFrame.

    :param df_in: input DataFrame with columns: 
                  [time, open, high, low, close, volume].
    :param conversion_len: Tenkan-sen period
    :param base_len:       Kijun-sen period
    :param lagging_len:    Chikou Span shift
    :param leading_span_b_len: Senkou Span B period
    :param cloud_shift:    Forward shift for Span A/B
    :return: DataFrame with added Ichimoku columns
    """
    df = df_in.copy()

    # Tenkan-sen
    high_tenkan = df['high'].rolling(window=conversion_len).max()
    low_tenkan  = df['low'].rolling(window=conversion_len).min()
    df['tenkan_sen'] = (high_tenkan + low_tenkan) / 2

    # Kijun-sen
    high_kijun = df['high'].rolling(window=base_len).max()
    low_kijun  = df['low'].rolling(window=base_len).min()
    df['kijun_sen'] = (high_kijun + low_kijun) / 2

    # Chikou Span
    df['chikou_span'] = df['close'].shift(-lagging_len)

    # Extend index by cloud_shift rows
    additional_index = pd.Series([df.index[-1] + i + 1 for i in range(cloud_shift)], name='index')
    additional_rows = pd.DataFrame(index=additional_index, columns=df.columns)

    # Calculate next 'cloud_shift' dates for 'time' column
    last_date = datetime.strptime(df['time'].iloc[-1], '%Y-%m-%d')
    additional_rows['time'] = [(last_date + timedelta(days=i+1)).strftime('%Y-%m-%d')
                               for i in range(cloud_shift)]

    # Drop columns that are all NaN (avoid warnings) and concat
    additional_rows = additional_rows.dropna(axis=1, how='all')
    df = pd.concat([df, additional_rows])

    # Senkou Span A (Leading Span A)
    df['senkou_span_a'] = ((df['tenkan_sen'] + df['kijun_sen']) / 2).shift(cloud_shift)

    # Senkou Span B (Leading Span B)
    period_senkou_high = df['high'].rolling(window=leading_span_b_len).max()
    period_senkou_low  = df['low'].rolling(window=leading_span_b_len).min()
    df['senkou_span_b'] = ((period_senkou_high + period_senkou_low) / 2).shift(cloud_shift)

    # Optional cloud color column if you want to highlight bullish/bearish cloud
    df['cloud_color'] = np.where(df['senkou_span_a'] > df['senkou_span_b'], LIGHT_GREEN, LIGHT_RED)

    return df