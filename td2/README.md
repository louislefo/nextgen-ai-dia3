# TD 2: Majority Voting Consensus & Dynamic Model Routing

ESILV - Data & Artificial Intelligence Major (Year 4 / S7)  
Course: Next-Generation AI - Trustworthy Generative AI (Didier Parisot)  
Sub-group: DIA 3  

---

## Overview

TD 2 focuses on two core architectures for trustworthy generative AI:
1. **Majority Voting Consensus (`atelier-vote.py` / `vote_k_sur_n`)**: Implementing a $k$-of-$n$ quorum mechanism across multiple heterogeneous LLM outputs to detect divergences, eliminate syntax hallucinations, and flag unsafe answers before execution.
2. **Dynamic Request Routing (`atelier-routage.py`)**: Designing an automated routing rule that inspects question complexity (period vs. completed age vs. product conditions) and routes queries to the most cost-effective model that satisfies the reliability threshold.

---

## Files in this Directory

- `atelier-vote.py`: Simulation and evaluation harness for $k$-of-$n$ consensus voting mechanisms.
- `atelier-routage.py`: Benchmarking harness for dynamic model routing strategies across different difficulty scenarios.
