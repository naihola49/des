import pandas as pd
import numpy as np
from sklearn.feature_selection import mutual_info_regression
import matplotlib.pyplot as plt
import seaborn as sns


def analyze_feature_informativeness(X, y, feature_names, target_name="Target", 
                                    top_n=15, plot=True, figsize=(14, 6)):
    """
    Analyze feature informativeness using correlation and mutual information.
    
    Args:
        X (pd.DataFrame or np.array): Feature matrix
        y (pd.Series or np.array): Target variable
        feature_names (list): List of feature names (must match X columns/indices)
        target_name (str): Name of target for display
        top_n (int): Number of top features to display
        plot (bool): Whether to create visualizations
        figsize (tuple): Figure size for plots
    
    Returns:
        dict: Contains:
            - 'correlation_df' (pd.DataFrame): Features sorted by absolute correlation
            - 'mi_df' (pd.DataFrame): Features sorted by mutual information
            - 'combined_df' (pd.DataFrame): Merged correlation and MI with rankings
            - 'summary' (dict): Summary statistics
    """
    # Convert to DataFrame if needed
    if isinstance(X, np.ndarray):
        X = pd.DataFrame(X, columns=feature_names)
    elif isinstance(X, pd.DataFrame):
        # Ensure feature names match
        if X.columns.tolist() != feature_names:
            X.columns = feature_names
    
    if isinstance(y, np.ndarray):
        y = pd.Series(y, name=target_name)
    
    # Prepare data (drop NaN in target)
    diagnostic_df = pd.concat([X, y], axis=1).dropna(subset=[y.name])
    X_clean = diagnostic_df[feature_names]
    y_clean = diagnostic_df[y.name]
        
    # 1. Correlation Analysis
    print("CORRELATION ANALYSIS (Linear Relationships)")

    correlations = X_clean.corrwith(y_clean).sort_values(key=abs, ascending=False)
    corr_df = pd.DataFrame({
        'Feature': correlations.index,
        'Correlation': correlations.values,
        'Abs_Correlation': correlations.abs().values
    }).sort_values('Abs_Correlation', ascending=False)
    
    print(f"\nTop {top_n} features by absolute correlation:")
    print(corr_df.head(top_n).to_string(index=False))
    
    print(f"\nSummary:")
    print(f"  Features with |correlation| > 0.1: {(corr_df['Abs_Correlation'] > 0.1).sum()}")
    print(f"  Features with |correlation| > 0.3: {(corr_df['Abs_Correlation'] > 0.3).sum()}")
    print(f"  Features with |correlation| > 0.5: {(corr_df['Abs_Correlation'] > 0.5).sum()}")
    print(f"  Max correlation: {corr_df['Abs_Correlation'].max():.3f}")
    print(f"  Mean |correlation|: {corr_df['Abs_Correlation'].mean():.3f}")
    
    # 2. Mutual Information Analysis
    print("\n")
    print("MUTUAL INFORMATION ANALYSIS (Linear + Non-linear Relationships)")
    
    mi_scores = mutual_info_regression(X_clean, y_clean, random_state=42, n_neighbors=3)
    
    mi_df = pd.DataFrame({
        'Feature': feature_names,
        'Mutual_Information': mi_scores
    }).sort_values('Mutual_Information', ascending=False)
    
    print(f"\nTop {top_n} features by mutual information:")
    print(mi_df.head(top_n).to_string(index=False))
    
    print(f"\nSummary:")
    print(f"  Features with MI > 0.01: {(mi_df['Mutual_Information'] > 0.01).sum()}")
    print(f"  Features with MI > 0.05: {(mi_df['Mutual_Information'] > 0.05).sum()}")
    print(f"  Features with MI > 0.1: {(mi_df['Mutual_Information'] > 0.1).sum()}")
    print(f"  Max MI: {mi_df['Mutual_Information'].max():.3f}")
    print(f"  Mean MI: {mi_df['Mutual_Information'].mean():.3f}")
    
    # 3. Combined Analysis
    print("\n")
    print("COMBINED FEATURE RANKING")
    
    # Merge correlation and MI
    combined_df = corr_df.merge(mi_df, on='Feature')
    combined_df['Corr_Rank'] = combined_df['Abs_Correlation'].rank(ascending=False)
    combined_df['MI_Rank'] = combined_df['Mutual_Information'].rank(ascending=False)
    combined_df['Avg_Rank'] = (combined_df['Corr_Rank'] + combined_df['MI_Rank']) / 2
    
    combined_df = combined_df.sort_values('Avg_Rank')
    
    print(f"\nTop {top_n} features (by average rank of correlation + MI):")
    print(combined_df[['Feature', 'Correlation', 'Mutual_Information', 'Avg_Rank']].head(top_n).to_string(index=False))
    
    # Identify features informative in both metrics
    informative_both = combined_df[
        (combined_df['Abs_Correlation'] > 0.1) & (combined_df['Mutual_Information'] > 0.01)
    ]
    print(f"\nFeatures informative in BOTH metrics (|corr| > 0.1 AND MI > 0.01):")
    print(f"  Count: {len(informative_both)}")
    if len(informative_both) > 0:
        print(informative_both[['Feature', 'Correlation', 'Mutual_Information']].to_string(index=False))
    
    # Create summary dictionary
    summary = {
        'n_features': len(feature_names),
        'n_high_corr': (corr_df['Abs_Correlation'] > 0.3).sum(),
        'n_high_mi': (mi_df['Mutual_Information'] > 0.1).sum(),
        'n_informative_both': len(informative_both),
        'max_correlation': corr_df['Abs_Correlation'].max(),
        'max_mi': mi_df['Mutual_Information'].max(),
        'mean_correlation': corr_df['Abs_Correlation'].mean(),
        'mean_mi': mi_df['Mutual_Information'].mean()
    }
    
    # 4. Visualization
    if plot:
        fig, axes = plt.subplots(1, 2, figsize=figsize)
        
        # Plot 1: Correlation
        ax1 = axes[0]
        top_corr = corr_df.head(top_n)
        ax1.barh(range(len(top_corr)), top_corr['Correlation'].values)
        ax1.set_yticks(range(len(top_corr)))
        ax1.set_yticklabels(top_corr['Feature'].values, fontsize=8)
        ax1.set_xlabel('Correlation with Target', fontsize=10)
        ax1.set_title(f'Top {top_n} Features by Correlation', fontsize=12, fontweight='bold')
        ax1.axvline(0, color='black', linestyle='-', linewidth=0.5)
        ax1.grid(True, alpha=0.3, axis='x')
        
        # Plot 2: Mutual Information
        ax2 = axes[1]
        top_mi = mi_df.head(top_n)
        ax2.barh(range(len(top_mi)), top_mi['Mutual_Information'].values, color='orange')
        ax2.set_yticks(range(len(top_mi)))
        ax2.set_yticklabels(top_mi['Feature'].values, fontsize=8)
        ax2.set_xlabel('Mutual Information', fontsize=10)
        ax2.set_title(f'Top {top_n} Features by Mutual Information', fontsize=12, fontweight='bold')
        ax2.grid(True, alpha=0.3, axis='x')
        
        plt.tight_layout()
        plt.show()
        
        # Scatter plot: Correlation vs MI
        fig, ax = plt.subplots(figsize=(10, 8))
        ax.scatter(combined_df['Abs_Correlation'], combined_df['Mutual_Information'], alpha=0.6)
        ax.set_xlabel('Absolute Correlation', fontsize=12)
        ax.set_ylabel('Mutual Information', fontsize=12)
        ax.set_title(f'Feature Informativeness: Correlation vs Mutual Information\n({target_name})', 
                    fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        
        # Annotate top features
        top_features = combined_df.head(5)
        for _, row in top_features.iterrows():
            ax.annotate(row['Feature'], 
                       (row['Abs_Correlation'], row['Mutual_Information']),
                       fontsize=8, alpha=0.7)
        
        plt.tight_layout()
        plt.show()
    
    return {
        'correlation_df': corr_df,
        'mi_df': mi_df,
        'combined_df': combined_df,
        'summary': summary
    }
