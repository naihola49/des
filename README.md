# AI-Powered Factory Simulation

## Motivation

After trying to make predictions on data from a singular production run in a continuous process plant, I quickly realized that predictions in dynamic environments are not powerful. A myriad of factors contribute to poor prediction performance (e.g. machine steady state & data drift, unobserved environmental variables, sensor resets and machine failure, changing material inputs). Elegant algorithms, big data, and compute cannot replace years of intuition and operating experience.

Rather than replacing shop-floor action through prediction, compute should augment operators’ decision-making. Simulation is a better fit: plant managers and operators can test intuition and decisions, observe outcomes, and iterate without large capital expense in a capital-intense industry.

## The Tool

Discrete-event simulation meets LLM capabilities. **Describe** your factory in natural language (source, stations, buffers, rework, sink) and the LLM generates a factory graph—nodes, edges, and probabilistic routing (e.g. rework feeding back into machines). **Design** in an interactive canvas (React Flow): add or edit nodes, set processing-time and demand distributions, buffer capacity, and rework probabilities. **Simulate** with Monte Carlo (configurable N trials) to get throughput, cycle time, and percentile metrics. **Interpret** with an LLM that summarizes the results, identifies bottlenecks, and suggests operational improvements.

Rather than trying to replace shop-floor action through prediction, compute should serve to augment operator's decision-making. Simulation serves as a much better tool; plant managers and operators may test their intuition and decisions, observe an experiment's outcomes, and execute without large capital expense in a very capital intense industry.

### Updates
March 12, 2026: Added manual processing station following a Weibull distribution (scale parameter measured by hours since last break). Entity processing time is sampled at beginning of processing timemanual machine (not at arrival, queueing delay should not factor into operator fatigue for distinct entity). Logic: operators fatigue over time; rather than entity's records being sampled before processing and stored in event queue, processing is now system dependent.
