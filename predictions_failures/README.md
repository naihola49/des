# Predictions Failing in Noisy Manufacturing Environments

## The Challenge

Manufacturing systems are fundamentally different from the controlled environments where machine learning typically excels.
From my experience learning this models in academicia, all data is typically static; relationships can be found with extensive pre-processing and the underlying distributions which these sophisticated algorithms learn from are stable.

In noisy environments such as manufacturing, operations are monitored and decisions are made in real-time. Setpoints/inputs are tuned according to current process readings. The inherent reactivity of operations on ever-fluctuating environments combined with unplanned physical errors (e.g. machine downtime, sensor resets) leads to extremely poor predictions, practically useless for an operator.  

Results from ML-modeling:
- Train Performance: Models achieved excellent fit (R² = 0.54-0.96) on training data
- Test Performance: Catastrophic failure (median R² = -12.14, worst case R² < -10³⁰). Guessing the average is far more effective than using our predictions.

**The Data Cannot Capture Reality:**
Even with 568 carefully engineered features (raw material properties, process variables, rolling statistics, sensor reset indicators), we cannot capture the operator's mental model, their real-time decision-making process, or their response to unmeasured quality signals.
