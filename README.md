# AI-Powered Factory Simulation

## Motivation

After trying to make predictions on data from a singular production run in a continuous process plant, I quickly realized that predictions in dynamic environments are not powerful. A myriad of factors contribute to poor prediction performance (e.g. machine steady state & data drift, unobserved environmental variables, sensor resets and machine failure, changing material inputs). Elegant algorithms, big data, and compute cannot replace years of intuition and operating experience.

Rather than replacing shop-floor action through prediction, compute should augment operators’ decision-making. Simulation is a better fit: plant managers and operators can test intuition and decisions, observe outcomes, and iterate without large capital expense in a capital-intense industry.

## The Tool

Discrete-event simulation meets LLM capabilities. **Describe** your factory in natural language (source, stations, buffers, rework, sink) and the LLM generates a factory graph—nodes, edges, and probabilistic routing (e.g. rework feeding back into machines). **Design** in an interactive canvas (React Flow): add or edit nodes, set processing-time and demand distributions, buffer capacity, and rework probabilities. **Simulate** with Monte Carlo (configurable N trials) to get throughput, cycle time, and percentile metrics. **Interpret** with an LLM that summarizes the results, identifies bottlenecks, and suggests operational improvements.

Rather than trying to replace shop-floor action through prediction, compute should serve to augment operator's decision-making. Simulation serves as a much better tool; plant managers and operators may test their intuition and decisions, observe an experiment's outcomes, and execute without large capital expense in a very capital intense industry.

## The Tool:
Discrete Event Simulation meets LLM capabilities. First, describe your factory in natural language (machine/station, source, rework, sink/finished goods, buffer) and the LLM will generate the necessary factory floor graph connecting each node to its correct prior and subsequent node. The user then may adjust parameters (e.g. statistical distributions, buffer size) that aligns with the current physical layout. Experiments then can be ran to determine the effect of added/lost capacity on process. Finally, the LLM distills insights, mentioning natural bottlenecks and constraints in factory design. 