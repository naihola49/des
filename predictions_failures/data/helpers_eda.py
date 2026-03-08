import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.signal import correlate

# Function to plot distribution of a single measurement
def plot_measurement_distribution(col_name, df, ax, exclude_zeros=False, location_num=None):
    """
    Plot distribution (histogram + KDE) for a single measurement column.
    
    Args:
        col_name (str): Name of the column to plot
        df (pd.DataFrame): DataFrame containing the data
        ax (matplotlib.axes): Axis to plot on (required)
        exclude_zeros (bool): Whether to exclude zero values (sensor resets). Default False.
        location_num (int): Location number for title (1-indexed). If None, extracted from col_name.
    
    Returns:
        matplotlib.axes: The axis object
    """
    data = df[col_name].copy()
    
    # Exclude zeros if requested
    if exclude_zeros:
        data = data[data != 0]
    
    # Plot histogram
    ax.hist(data, bins=50, alpha=0.6, density=True, edgecolor='black')
    
    # Plot KDE (kernel density estimate)
    try:
        if len(data) > 0:
            kde = stats.gaussian_kde(data)
            x_range = np.linspace(data.min(), data.max(), 200)
            ax.plot(x_range, kde(x_range), 'r-', linewidth=2, alpha=0.8)
    except:
        pass
    
    # Add statistics
    mean_val = data.mean()
    std_val = data.std()
    median_val = data.median()
    zero_count = (df[col_name] == 0).sum()  # Count zeros from original data
    
    ax.axvline(mean_val, color='green', linestyle='--', linewidth=1.5, alpha=0.7)
    ax.axvline(median_val, color='orange', linestyle='--', linewidth=1.5, alpha=0.7)
    
    # Extract location number if not provided (1-indexed: Measurement0 -> Location 1)
    if location_num is None:
        try:
            meas_num = int(col_name.replace('Stage1.Output.Measurement', '').replace('.U.Actual', ''))
            location_num = meas_num + 1
        except:
            location_num = col_name
    
    # Set title with location number and statistics
    ax.set_title(f'Location {location_num}\nμ={mean_val:.2f}, σ={std_val:.2f}, Zeros: {zero_count}', 
                 fontsize=9, pad=3)
    ax.set_xlabel('Value', fontsize=7)
    ax.set_ylabel('Density', fontsize=7)
    ax.tick_params(labelsize=6)
    ax.grid(True, alpha=0.3)
    
    return ax


# Function to plot machine variables in a grid layout
def plot_machine_variables(machine_cols, machine_name, df):
    """
    Plots all variables for a given machine in a grid layout.

    Args:
        machine_cols (list): List of column names for the machine.
        machine_name (str): Name of the machine (str for figure title).
        df (pd.DataFrame): DataFrame containing the data.
    """
    if len(machine_cols) > 0:
        n_cols_plot = min(4, len(machine_cols))
        n_rows_plot = (len(machine_cols) + n_cols_plot - 1) // n_cols_plot

        fig, axes = plt.subplots(n_rows_plot, n_cols_plot, figsize=(16, 4 * n_rows_plot))
        fig.suptitle(f'{machine_name} Variables', fontsize=14)
        if n_rows_plot == 1:
            axes = axes.reshape(1, -1) if n_cols_plot > 1 else [axes]
        axes = axes.flatten()

        for idx, col in enumerate(machine_cols):
            ax = axes[idx]
            ax.plot(df['time_stamp'], df[col], linewidth=0.8, alpha=0.8)
            ax.set_title(col, fontsize=8, pad=2)
            ax.set_xlabel('Time', fontsize=6)
            ax.set_ylabel('Value', fontsize=6)
            ax.tick_params(labelsize=6)
            ax.grid(True, alpha=0.3)

        for idx in range(len(machine_cols), len(axes)):
            axes[idx].axis('off')

        plt.tight_layout()
        plt.show()


# Function to compute time lagged correlation
def compute_time_lagged_correlation(series1, series2, max_lag=None, method='pearson', 
                                     return_all_lags=False, plot=False):
    """
    Compute cross-correlation between two time series at different time lags.
    
    This function helps identify:
    - Flow direction: If series1 leads series2, positive lag indicates series1 -> series2
    - Flow time: The lag with maximum correlation estimates time delay
    - Process relationships: Strong correlations indicate connected processes
    
    Args:
        series1 (pd.Series or np.array): First time series (typically upstream/earlier)
        series2 (pd.Series or np.array): Second time series (typically downstream/later)
        max_lag (int): Maximum lag to test (in time steps). If None, uses 10% of data length.
        method (str): Correlation method - 'pearson' (linear) or 'spearman' (rank-based)
        return_all_lags (bool): If True, returns correlation at all lags. If False, only optimal lag.
        plot (bool): If True, plots cross-correlation function
    
    Returns:
        dict: Contains:
            - 'optimal_lag' (int): Lag with maximum absolute correlation
            - 'optimal_correlation' (float): Correlation at optimal lag
            - 'all_lags' (np.array): All tested lags (if return_all_lags=True)
            - 'all_correlations' (np.array): Correlations at all lags (if return_all_lags=True)
            - 'interpretation' (str): Human-readable interpretation
    """
    # Convert to numpy arrays and handle missing values
    s1 = np.array(series1)
    s2 = np.array(series2)
    
    # Remove NaN values (align both series)
    valid_mask = ~(np.isnan(s1) | np.isnan(s2))
    s1 = s1[valid_mask]
    s2 = s2[valid_mask]
    
    if len(s1) < 10:
        raise ValueError("Not enough valid data points after removing NaNs")
    
    # Set default max_lag
    if max_lag is None:
        max_lag = max(50, len(s1) // 10)  # At least 50 lags or 10% of data
    
    # Limit max_lag to reasonable range
    max_lag = min(max_lag, len(s1) // 2)
    
    # Compute correlations at different lags
    lags = np.arange(-max_lag, max_lag + 1)
    correlations = []
    
    for lag in lags:
        if lag == 0:
            # No lag - direct correlation
            if method == 'pearson':
                corr = np.corrcoef(s1, s2)[0, 1]
            else:  # spearman
                corr, _ = stats.spearmanr(s1, s2)
        elif lag > 0:
            # Positive lag: series1[t] vs series2[t+lag]
            # This means series1 leads series2 (series1 happens BEFORE series2)
            if len(s1) > lag:
                s1_shifted = s1[:-lag]
                s2_shifted = s2[lag:]
                if len(s1_shifted) > 1 and len(s2_shifted) > 1:
                    if method == 'pearson':
                        corr = np.corrcoef(s1_shifted, s2_shifted)[0, 1]
                    else:
                        corr, _ = stats.spearmanr(s1_shifted, s2_shifted)
                else:
                    corr = np.nan
            else:
                corr = np.nan
        else:  # lag < 0
            # Negative lag: series1[t+|lag|] vs series2[t]
            lag_abs = abs(lag)
            if len(s1) > lag_abs:
                s1_shifted = s1[lag_abs:]
                s2_shifted = s2[:-lag_abs]
                if len(s1_shifted) > 1 and len(s2_shifted) > 1:
                    if method == 'pearson':
                        corr = np.corrcoef(s1_shifted, s2_shifted)[0, 1]
                    else:
                        corr, _ = stats.spearmanr(s1_shifted, s2_shifted)
                else:
                    corr = np.nan
            else:
                corr = np.nan
        
        correlations.append(corr)
    
    correlations = np.array(correlations)
    
    # Find optimal lag (maximum absolute correlation)
    valid_corrs = np.isfinite(correlations)
    if not np.any(valid_corrs):
        raise ValueError("No valid correlations found")
    
    optimal_idx = np.nanargmax(np.abs(correlations))
    optimal_lag = lags[optimal_idx]
    optimal_correlation = correlations[optimal_idx]
    
    # Create interpretation
    if optimal_lag > 0:
        interpretation = f"series1 leads series2 by {optimal_lag} time steps (series1 -> series2)"
    elif optimal_lag < 0:
        interpretation = f"series2 leads series1 by {abs(optimal_lag)} time steps (series2 -> series1)"
    else:
        interpretation = "No significant lag (contemporaneous correlation)"
    
    result = {
        'optimal_lag': int(optimal_lag),
        'optimal_correlation': float(optimal_correlation),
        'interpretation': interpretation
    }
    
    if return_all_lags:
        result['all_lags'] = lags
        result['all_correlations'] = correlations
    
    # Plot if requested
    if plot:
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(lags, correlations, 'b-', linewidth=2, alpha=0.7)
        ax.axvline(optimal_lag, color='r', linestyle='--', linewidth=2, 
                   label=f'Optimal lag: {optimal_lag}')
        ax.axhline(0, color='k', linestyle='-', linewidth=0.5, alpha=0.3)
        ax.set_xlabel('Lag (time steps)', fontsize=12)
        ax.set_ylabel(f'{method.capitalize()} Correlation', fontsize=12)
        ax.set_title(f'Cross-Correlation Function\nOptimal: lag={optimal_lag}, r={optimal_correlation:.3f}', 
                     fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend()
        plt.tight_layout()
        plt.show()
    
    return result


def compute_lag_matrix(series_dict, max_lag=None, method='pearson', location_names=None):
    """
    Compute optimal lag and correlation matrix for multiple time series.
    
    Useful for exploring flow patterns where locations are measured at different
    positions along a flow path (e.g., 15 locations along a combiner).
    
    Args:
        series_dict (dict): Dictionary of {name: series} pairs, e.g., 
                           {'Location1': df['col1'], 'Location2': df['col2']}
        max_lag (int): Maximum lag to test. If None, uses 50 or 10% of data length.
        method (str): Correlation method - 'pearson' or 'spearman'
        location_names (list): Optional list of location names for ordering.
                              If None, uses keys from series_dict.
    
    Returns:
        dict: Contains:
            - 'lag_matrix' (pd.DataFrame): Matrix of optimal lags (rows lead columns)
            - 'correlation_matrix' (pd.DataFrame): Matrix of correlations at optimal lags
            - 'location_order' (list): Order of locations (upstream to downstream if detected)
    """
    if location_names is None:
        location_names = list(series_dict.keys())
    
    n_locations = len(location_names)
    lag_matrix = np.zeros((n_locations, n_locations))
    corr_matrix = np.zeros((n_locations, n_locations))
    
    # Compute pairwise correlations
    for i, loc1 in enumerate(location_names):
        for j, loc2 in enumerate(location_names):
            if i == j:
                # Same location - no lag, perfect correlation
                lag_matrix[i, j] = 0
                corr_matrix[i, j] = 1.0
            else:
                try:
                    result = compute_time_lagged_correlation(
                        series_dict[loc1], 
                        series_dict[loc2],
                        max_lag=max_lag,
                        method=method,
                        return_all_lags=False,
                        plot=False
                    )
                    lag_matrix[i, j] = result['optimal_lag']
                    corr_matrix[i, j] = result['optimal_correlation']
                except Exception as e:
                    lag_matrix[i, j] = np.nan
                    corr_matrix[i, j] = np.nan
    
    # Convert to DataFrames
    lag_df = pd.DataFrame(lag_matrix, index=location_names, columns=location_names)
    corr_df = pd.DataFrame(corr_matrix, index=location_names, columns=location_names)
    
    # Try to infer flow order (locations with more positive lags leading others are upstream)
    lag_sums = lag_df.sum(axis=1)
    if not lag_sums.isna().all():
        # Locations with more positive lag sums are upstream
        inferred_order = lag_sums.sort_values(ascending=False).index.tolist()
    else:
        inferred_order = location_names
    
    return {
        'lag_matrix': lag_df,
        'correlation_matrix': corr_df,
        'location_order': inferred_order
    }


def plot_lag_matrix(lag_matrix, correlation_matrix=None, title="Lag Matrix", 
                    figsize=(12, 10), cmap='RdBu_r'):
    """
    Visualize the lag matrix as a heatmap.
    
    Args:
        lag_matrix (pd.DataFrame): Matrix of optimal lags
        correlation_matrix (pd.DataFrame): Optional matrix of correlations for overlay
        title (str): Plot title
        figsize (tuple): Figure size
        cmap (str): Colormap for lag visualization
    """
    fig, axes = plt.subplots(1, 2 if correlation_matrix is not None else 1, 
                            figsize=figsize if correlation_matrix is None else (figsize[0]*2, figsize[1]))
    
    if correlation_matrix is None:
        axes = [axes]
    
    # Plot lag matrix
    im1 = axes[0].imshow(lag_matrix.values, cmap=cmap, aspect='auto')
    axes[0].set_xticks(range(len(lag_matrix.columns)))
    axes[0].set_yticks(range(len(lag_matrix.index)))
    axes[0].set_xticklabels(lag_matrix.columns, rotation=45, ha='right')
    axes[0].set_yticklabels(lag_matrix.index)
    axes[0].set_title(f'{title} - Optimal Lags', fontsize=14, fontweight='bold')
    axes[0].set_xlabel('Location (Downstream)', fontsize=12)
    axes[0].set_ylabel('Location (Upstream)', fontsize=12)
    
    # Add text annotations for lag values
    for i in range(len(lag_matrix.index)):
        for j in range(len(lag_matrix.columns)):
            lag_val = lag_matrix.iloc[i, j]
            if not np.isnan(lag_val):
                text_color = 'white' if abs(lag_val) > abs(lag_matrix.values).max() * 0.5 else 'black'
                axes[0].text(j, i, f'{int(lag_val)}', 
                            ha='center', va='center', color=text_color, fontsize=8)
    
    plt.colorbar(im1, ax=axes[0], label='Lag (time steps)')
    
    # Plot correlation matrix if provided
    if correlation_matrix is not None:
        im2 = axes[1].imshow(correlation_matrix.values, cmap='coolwarm', 
                            aspect='auto', vmin=-1, vmax=1)
        axes[1].set_xticks(range(len(correlation_matrix.columns)))
        axes[1].set_yticks(range(len(correlation_matrix.index)))
        axes[1].set_xticklabels(correlation_matrix.columns, rotation=45, ha='right')
        axes[1].set_yticklabels(correlation_matrix.index)
        axes[1].set_title(f'{title} - Correlations at Optimal Lags', fontsize=14, fontweight='bold')
        axes[1].set_xlabel('Location', fontsize=12)
        axes[1].set_ylabel('Location', fontsize=12)
        
        # Add text annotations for correlation values
        for i in range(len(correlation_matrix.index)):
            for j in range(len(correlation_matrix.columns)):
                corr_val = correlation_matrix.iloc[i, j]
                if not np.isnan(corr_val):
                    text_color = 'white' if abs(corr_val) > 0.5 else 'black'
                    axes[1].text(j, i, f'{corr_val:.2f}', 
                                ha='center', va='center', color=text_color, fontsize=8)
        
        plt.colorbar(im2, ax=axes[1], label='Correlation')
    
    plt.tight_layout()
    plt.show()


def analyze_flow_pattern(lag_matrix, location_names=None):
    """
    Analyze the lag matrix to infer flow direction and pattern.
    
    Args:
        lag_matrix (pd.DataFrame): Matrix of optimal lags
        location_names (list): Optional list of location names
    
    Returns:
        dict: Contains:
            - 'flow_order' (list): Inferred order from upstream to downstream
            - 'flow_times' (dict): Estimated flow times between adjacent locations
            - 'is_sequential' (bool): Whether flow appears sequential (1->2->3...)
            - 'summary' (str): Human-readable summary
    """
    if location_names is None:
        location_names = lag_matrix.index.tolist()
    
    # Calculate how much each location leads others (sum of positive lags)
    lead_scores = {}
    for loc in location_names:
        # Sum of lags where this location leads others (positive values in row)
        leads = lag_matrix.loc[loc, :].values
        lead_score = np.nansum(leads[leads > 0]) - np.nansum(np.abs(leads[leads < 0]))
        lead_scores[loc] = lead_score
    
    # Sort by lead score (highest = most upstream)
    flow_order = sorted(lead_scores.keys(), key=lambda x: lead_scores[x], reverse=True)
    
    # Calculate flow times between adjacent locations in inferred order
    flow_times = {}
    for i in range(len(flow_order) - 1):
        loc1 = flow_order[i]
        loc2 = flow_order[i + 1]
        lag = lag_matrix.loc[loc1, loc2]
        if not np.isnan(lag) and lag > 0:
            flow_times[f'{loc1} -> {loc2}'] = lag
    
    # Check if flow is sequential (locations in numeric order)
    try:
        # Try to extract numeric order from location names
        numeric_order = [int(''.join(filter(str.isdigit, loc))) for loc in location_names]
        is_sequential = flow_order == sorted(location_names, 
                                           key=lambda x: int(''.join(filter(str.isdigit, x))))
    except:
        is_sequential = False
    
    # Create summary
    summary = f"Flow Order (upstream -> downstream): {' -> '.join(flow_order)}\n"
    summary += f"Flow appears sequential: {is_sequential}\n"
    summary += f"Flow times between adjacent locations:\n"
    for path, time in flow_times.items():
        summary += f"  {path}: {time} time steps\n"
    
    return {
        'flow_order': flow_order,
        'flow_times': flow_times,
        'is_sequential': is_sequential,
        'summary': summary
    }